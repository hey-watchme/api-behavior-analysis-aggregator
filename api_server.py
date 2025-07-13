#!/usr/bin/env python3
"""
SED集計・アップロードAPI サーバー

FastAPIを使用してSED分析機能をREST APIとして提供する。
ダッシュボードやWebアプリケーションから呼び出し可能。
"""

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid
import json
import os
from datetime import datetime
import logging

from sed_aggregator import SEDAggregator
from upload_sed_summary import SEDSummaryUploader

# FastAPIアプリ設定
app = FastAPI(
    title="SED分析API",
    description="音響イベント検出データの収集・集計・アップロードAPI",
    version="1.0.0"
)

# CORS設定を追加
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では適切に制限してください
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# タスク状況管理
task_status: Dict[str, Dict[str, Any]] = {}


class AnalysisRequest(BaseModel):
    """分析リクエストモデル"""
    device_id: str
    date: str  # YYYY-MM-DD形式


class TaskStatus(BaseModel):
    """タスク状況モデル"""
    task_id: str
    status: str  # started, running, completed, failed
    message: str
    progress: Optional[int] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@app.get("/", tags=["Health"])
async def root():
    """ヘルスチェック"""
    return {
        "service": "SED分析API", 
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {"status": "healthy"}


@app.post("/analysis/sed", response_model=Dict[str, str], tags=["Analysis"])
async def start_sed_analysis(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """
    SED分析を開始（非同期バックグラウンド実行）
    """
    # 日付形式検証
    try:
        datetime.strptime(request.date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="日付はYYYY-MM-DD形式で指定してください")
    
    # タスクID生成
    task_id = str(uuid.uuid4())
    
    # タスク状況初期化
    task_status[task_id] = {
        "task_id": task_id,
        "status": "started",
        "message": "分析タスクを開始しました",
        "progress": 0,
        "device_id": request.device_id,
        "date": request.date,
        "created_at": datetime.now().isoformat()
    }
    
    # バックグラウンドタスク追加
    background_tasks.add_task(execute_sed_analysis, task_id, request.device_id, request.date)
    
    logger.info(f"SED分析開始: task_id={task_id}, device_id={request.device_id}, date={request.date}")
    
    return {
        "task_id": task_id,
        "status": "started",
        "message": f"{request.device_id}/{request.date} の分析を開始しました"
    }


@app.get("/analysis/sed/{task_id}", response_model=TaskStatus, tags=["Analysis"])
async def get_analysis_status(task_id: str):
    """
    分析タスクの状況を取得
    """
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="タスクが見つかりません")
    
    return task_status[task_id]


@app.get("/analysis/sed", tags=["Analysis"])
async def list_analysis_tasks():
    """
    全分析タスクの一覧を取得
    """
    return {
        "tasks": list(task_status.values()),
        "total": len(task_status)
    }


@app.delete("/analysis/sed/{task_id}", tags=["Analysis"])
async def delete_analysis_task(task_id: str):
    """
    完了・失敗したタスクを削除
    """
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="タスクが見つかりません")
    
    task = task_status[task_id]
    if task["status"] in ["running", "started"]:
        raise HTTPException(status_code=400, detail="実行中のタスクは削除できません")
    
    del task_status[task_id]
    return {"message": f"タスク {task_id} を削除しました"}


async def execute_sed_analysis(task_id: str, device_id: str, date: str):
    """
    SED分析の実行（バックグラウンドタスク）
    """
    try:
        logger.info(f"🚀 バックグラウンドタスク開始: task_id={task_id}, device_id={device_id}, date={date}")
        
        # ステップ1: データ収集・集計
        task_status[task_id].update({
            "status": "running",
            "message": "データ収集・集計中...",
            "progress": 25
        })
        
        logger.info(f"📊 SEDAggregator インスタンス作成中...")
        aggregator = SEDAggregator()
        logger.info(f"📡 Supabaseからデータ取得開始...")
        result = await aggregator.run(device_id, date)
        logger.info(f"📄 データ取得結果: {result}")
        
        if not result["success"]:
            logger.error(f"❌ データ収集・保存失敗: {result.get('message', '不明なエラー')}")
            
            # データがない場合の適切なエラーメッセージ
            if result.get("reason") == "no_data":
                task_status[task_id].update({
                    "status": "failed",
                    "message": f"{date}のデータがありませんでした",
                    "error": result.get("message", "データが存在しません"),
                    "progress": 100
                })
            else:
                task_status[task_id].update({
                    "status": "failed",
                    "message": "データ収集に失敗しました",
                    "error": result.get("message", "不明なエラー"),
                    "progress": 100
                })
            return
        
        logger.info(f"✅ データ収集・Supabase保存成功")
        
        # ステップ2: アップロード
        task_status[task_id].update({
            "status": "running",
            "message": "アップロード中...",
            "progress": 75
        })
        
        logger.info(f"☁️ アップロード開始...")
        # SSL検証を無効化してダッシュボード環境での接続問題を回避
        verify_ssl = os.getenv('VERIFY_SSL', 'false').lower() == 'true'
        uploader = SEDSummaryUploader(verify_ssl=verify_ssl)
        upload_result = await uploader.run(device_id, date)
        logger.info(f"📤 アップロード結果: {upload_result}")
        
        logger.info(f"🎉 分析完了")
        
        # 成功
        task_status[task_id].update({
            "status": "completed",
            "message": "分析完了",
            "progress": 100,
            "result": {
                "message": "データはSupabaseのbehavior_summaryテーブルに保存されました",
                "upload": upload_result,
                "device_id": device_id,
                "date": date
            }
        })
        
        logger.info(f"✅ SED分析完了: task_id={task_id}")
        
    except Exception as e:
        logger.error(f"💥 SED分析エラー: task_id={task_id}, error={e}")
        logger.error(f"💥 エラー詳細: {type(e).__name__}: {str(e)}")
        import traceback
        logger.error(f"💥 スタックトレース: {traceback.format_exc()}")
        task_status[task_id].update({
            "status": "failed",
            "message": "分析中にエラーが発生しました",
            "error": str(e),
            "progress": 100
        })
        logger.error(f"❌ SED分析エラー: task_id={task_id}, error={e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010) 