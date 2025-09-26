#!/usr/bin/env python3
"""
SED（Sound Event Detection）データ集計ツール

Supabaseのbehavior_yamnetテーブル（現在はAST結果を格納）から音響イベント検出データを収集し、
日次集計結果をローカルに保存する。
"""

import asyncio
import json
import os
from pathlib import Path
from collections import Counter
from typing import Dict, List, Optional, Any
from datetime import datetime
import argparse
from supabase import create_client, Client
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

# 除外するイベントラベルのリスト
# これらのイベントは集計から完全に除外されます（ノイズや誤検出を減らすため）
EXCLUDED_EVENTS = [
    'Snake',       # ヘビ - 通常の生活環境では考えにくい
    'Insect',      # 昆虫 - 誤検出が多い
    'Cricket',     # コオロギ - 誤検出が多い
    'White noise', # ホワイトノイズ - 無意味な環境ノイズ
    'Mains hum',   # 電源ハム音 - 電気的ノイズ（50/60Hz）
    'Mouse',       # マウス - 誤検出が多いノイズ
    'Arrow',       # 矢 - 意味不明なイベント
]

# 優先順位カテゴリの定義（生活音表示用）
PRIORITY_CATEGORIES = {
    # 優先度1: 生体反応（健康モニタリングに重要）
    'biometric': [
        'Cough', 'Throat clearing', 'Sneeze', 'Sniff', 'Snoring', 'Breathing',
        'Gasp', 'Sigh', 'Hiccup', 'Burp, eructation', 'Yawn', 'Wheeze',
        'Pant', 'Snore', 'Chewing, mastication', 'Heartbeat'
    ],
    # 優先度2: 声・会話（社会活動の指標）
    'voice': [
        'Speech', 'Child speech, kid speaking', 'Conversation', 'Narration, monologue',
        'Babbling', 'Laughter', 'Baby laughter', 'Baby cry, infant cry',
        'Whimper', 'Crying, sobbing', 'Screaming', 'Shout', 'Children shouting',
        'Children playing', 'Whispering', 'Singing', 'Humming', 'Chatter',
        'Speech, human voice', 'Crowd', 'Call', 'Telephone bell ringing'
    ],
    # 優先度3: 生活音（日常活動の指標）
    'daily_life': [
        'Boiling', 'Water tap, faucet', 'Water', 'Pour', 'Dishes, pots, and pans',
        'Cutlery, silverware', 'Cupboard open or close', 'Microwave oven',
        'Blender', 'Sink (filling or washing)', 'Frying (food)', 'Kettle boiling',
        'Dishwasher', 'Door', 'Footsteps', 'Walk, footsteps', 'Keys jangling',
        'Drawer open or close', 'Typing', 'Computer keyboard', 'Toilet flush',
        'Television', 'Vacuum cleaner', 'Washing machine', 'Hair dryer',
        'Electric toothbrush', 'Bathtub (filling or washing)', 'Shower'
    ]
}

# 音の統合マッピング（類似音を統一）
SOUND_CONSOLIDATION = {
    # 水関連を「水の音」に統合
    'Water tap, faucet': '水の音',
    'Sink (filling or washing)': '水の音',
    'Water': '水の音',
    'Pour': '水の音',
    'Drip': '水の音',
    
    # タイピング・キーボード関連を「タイピング」に統合
    'Computer keyboard': 'タイピング',
    'Typing (computer)': 'タイピング',
    'Typing on a computer keyboard': 'タイピング',
    'Typing': 'タイピング',
    
    # 動物関連を「動物」に統合
    'Domestic animals, pets': '動物',
    'Livestock, farm animals, working animals': '動物',
    'Animal': '動物',
    'Pet': '動物',
    'Animal sounds': '動物',
    
    # 歩行関連を「足音」に統合
    'Walk, footsteps': '足音',
    'Footsteps': '足音',
    'Running': '足音',
    'Walking': '足音',
    
    # ドア関連を「ドア」に統合
    'Doorbell': 'ドア',
    'Door knocker': 'ドア',
    'Door lock, sign in, sign off': 'ドア',
    'Door': 'ドア',
    
    # 呼吸関連を「呼吸音」に統合
    'Respiratory sounds': '呼吸音',
    'Breathing': '呼吸音',
    
    # 咳関連を「咳」に統合
    'Cough': '咳',
    'Throat clearing': '咳',
    
    # 鳥関連を「鳥」に統合
    'Bird': '鳥',
    'Bird vocalization, bird call, bird song': '鳥',
    'Bird, bird song': '鳥',
    'Chirp, tweet': '鳥',
    
    # 食器・調理器具関連を統合
    'Dishes, pots, and pans': '食器の音',
    'Cutlery, silverware': '食器の音',
    'Clinking': '食器の音',
    
    # テレビ・音声メディアを統合
    'Television': 'テレビ',
    'Radio': 'テレビ',
    
    # 子供関連を統合
    'Child speech, kid speaking': '子供の声',
    'Children shouting': '子供の声',
    'Children playing': '子供の声',
    'Baby cry, infant cry': '赤ちゃんの泣き声',
    'Baby laughter': '赤ちゃんの笑い声',
    
    # 音楽関連を統合
    'Music': '音楽',
    'Musical instrument': '音楽',
    'Singing': '歌声',
    'Song': '歌声',
    
    # 会話・話し声を統合
    'Speech': '話し声',
    'Conversation': '話し声',
    'Speech, human voice': '話し声',
    'Narration, monologue': '話し声',
    
    # 笑い声を統合
    'Laughter': '笑い声',
    'Chuckle, chortle': '笑い声',
    'Giggle': '笑い声',
    
    # 引き出し・戸棚関連を統合
    'Drawer open or close': '戸棚・引き出し',
    'Cupboard open or close': '戸棚・引き出し',
    'Filing (rasp)': '戸棚・引き出し',
}

# AudioSetラベルの日本語訳対応表（AST/YAMNet共通）
AUDIOSET_LABEL_MAP = {
    'Speech': '話し声',
    'Child speech, kid speaking': '子供の話し声',
    'Conversation': '会話',
    'Narration, monologue': 'ナレーション・独り言',
    'Babbling': '赤ちゃんの喃語',
    'Speech synthesizer': '音声合成',
    'Shout': '叫び声',
    'Bellow': 'うなり声・叫び声',
    'Whoop': '叫び声・鬨の声',
    'Yell': 'エール・叫び声',
    'Children shouting': '子供の叫び声',
    'Screaming': '絶叫・悲鳴',
    'Whispering': 'ささやき声',
    'Laughter': '笑い声',
    'Baby laughter': '赤ちゃんの笑い声',
    'Giggle': 'くすくす笑い',
    'Snicker': '忍び笑い',
    'Belly laugh': '大笑い',
    'Chuckle, chortle': '含み笑い',
    'Crying, sobbing': '泣き声',
    'Baby cry, infant cry': '赤ちゃんの泣き声',
    'Whimper': 'すすり泣き',
    'Wail, moan': '嘆き声・うめき声',
    'Sigh': 'ため息',
    'Singing': '歌声',
    'Choir': '合唱',
    'Yodeling': 'ヨーデル',
    'Chant': '詠唱・チャント',
    'Mantra': 'マントラ',
    'Child singing': '子供の歌声',
    'Synthetic singing': '合成歌声',
    'Rapping': 'ラップ',
    'Humming': 'ハミング・鼻歌',
    'Hum': '低周波ノイズ',
    'Groan': 'うめき声',
    'Grunt': 'うなり声（不満など）',
    'Whistling': '口笛',
    'Breathing': '呼吸音',
    'Gasp': '息をのむ音',
    'Pant': 'あえぎ声',
    'Snore': 'いびき',
    'Cough': '咳',
    'Throat clearing': '咳',  # 咽頭クリア - 咳と統合
    'Sneeze': 'くしゃみ',
    'Sniff': '鼻をすする音',
    'Run': '走る音',
    'Shuffle': '足を引きずる音',
    'Walk, footsteps': '歩く音・足音',
    'Chewing, mastication': '咀嚼音',
    'Biting': '噛む音',
    'Gargling': 'うがい',
    'Burp, eructation': 'げっぷ',
    'Hiccup': 'しゃっくり',
    'Fart': 'おなら',
    'Hands': '手を使う音',
    'Finger snapping': '指パッチン',
    'Clapping': '拍手',
    'Heart sounds, heartbeat': '心音・心拍',
    'Heart murmur': '心雑音',
    'Cheering': '歓声',
    'Applause': '拍手喝采',
    'Chatter': 'おしゃべり・雑談',
    'Crowd': '群衆・人混み',
    'Hubbub, speech noise, speech babble': '喧騒・ガヤ',
    'Children playing': '子供の遊び声',
    'Animal': '動物',
    'Domestic animals, pets': 'ペット・家畜',
    'Dog': '犬',
    'Bark': '犬の吠え声',
    'Yip': 'キャンキャン鳴く声',
    'Howl': '遠吠え',
    'Bow-wow': 'ワンワン',
    'Growling': 'うなり声（犬など）',
    'Whimper (dog)': 'クーンという鳴き声',
    'Cat': '猫',
    'Purr': '猫が喉を鳴らす音',
    'Meow': '猫の鳴き声',
    'Hiss': 'シャーという威嚇音',
    'Caterwaul': '猫の叫び声',
    'Livestock, farm animals, working animals': '家畜・農場の動物',
    'Horse': '馬',
    'Clip-clop': '馬の蹄の音',
    'Neigh, whinny': '馬のいななき',
    'Cattle, bovinae': '牛',
    'Moo': '牛の鳴き声',
    'Cowbell': 'カウベル',
    'Pig': '豚',
    'Oink': '豚の鳴き声',
    'Goat': 'ヤギ',
    'Bleat': 'ヤギ・羊の鳴き声',
    'Sheep': '羊',
    'Fowl': 'ニワトリ',
    'Chicken, rooster': 'ニワトリ・雄鶏',
    'Cluck': 'コッコという鳴き声',
    'Crowing, cock-a-doodle-doo': '雄鶏の鳴き声',
    'Turkey': '七面鳥',
    'Gobble': '七面鳥の鳴き声',
    'Duck': 'アヒル',
    'Quack': 'アヒルの鳴き声',
    'Goose': 'ガチョウ',
    'Honk': 'ガチョウの鳴き声',
    'Wild animals': '野生動物',
    'Roaring cats (lions, tigers)': '大型ネコ科の咆哮',
    'Roar': '咆哮',
    'Bird': '鳥',
    'Bird vocalization, bird call, bird song': '鳥の鳴き声・さえずり',
    'Chirp, tweet': 'チュンチュン・さえずり',
    'Squawk': '鳥の金切り声',
    'Pigeon, dove': 'ハト',
    'Coo': 'ハトの鳴き声',
    'Crow': 'カラス',
    'Caw': 'カラスの鳴き声',
    'Owl': 'フクロウ',
    'Hoot': 'フクロウの鳴き声',
    'Bird flight, flapping wings': '鳥の羽ばたき',
    'Insect': '昆虫',
    'Cricket': 'コオロギ',
    'Mosquito': '蚊',
    'Fly, housefly': 'ハエ',
    'Buzz': 'ブーンという羽音',
    'Bee, wasp, etc.': 'ハチ・アブなど',
    'Frog': 'カエル',
    'Croak': 'カエルの鳴き声',
    'Snake': 'ヘビ',
    'Rattle': 'ガラガラヘビの音',
    'Whale vocalization': 'クジラの鳴き声',
    'Music': '音楽',
    'Musical instrument': '楽器',
    'Plucked string instrument': '撥弦楽器',
    'Guitar': 'ギター',
    'Acoustic guitar': 'アコースティックギター',
    'Steel guitar, slide guitar': 'スチールギター',
    'Electric guitar': 'エレキギター',
    'Banjo': 'バンジョー',
    'Sitar': 'シタール',
    'Mandolin': 'マンドリン',
    'Zither': 'ツィター',
    'Ukulele': 'ウクレレ',
    'Keyboard (musical)': '鍵盤楽器',
    'Piano': 'ピアノ',
    'Electric piano': '電子ピアノ',
    'Organ': 'オルガン',
    'Electronic organ': '電子オルガン',
    'Hammond organ': 'ハモンドオルガン',
    'Synthesizer': 'シンセサイザー',
    'Sampler': 'サンプラー',
    'Harpsichord': 'ハープシコード',
    'Percussion': '打楽器',
    'Drum kit': 'ドラムキット',
    'Drum machine': 'ドラムマシン',
    'Drum': 'ドラム',
    'Snare drum': 'スネアドラム',
    'Rimshot': 'リムショット',
    'Drum roll': 'ドラムロール',
    'Bass drum': 'バスドラム',
    'Timpani': 'ティンパニ',
    'Cymbal': 'シンバル',
    'Hi-hat': 'ハイハット',
    'Crash cymbal': 'クラッシュシンバル',
    'Tambourine': 'タンバリン',
    'Maraca': 'マラカス',
    'Rattle (instrument)': 'ガラガラ（楽器）',
    'Gong': 'ゴング・銅鑼',
    'Tubular bells': 'チューブラーベル',
    'Mallet percussion': 'マレット打楽器',
    'Marimba, xylophone': 'マリンバ・木琴',
    'Glockenspiel': 'グロッケンシュピール',
    'Vibraphone': 'ヴィブラフォン',
    'Steelpan': 'スチールドラム',
    'Triangle': 'トライアングル',
    'Wood block': 'ウッドブロック',
    'Castanets': 'カスタネット',
    'Claves': 'クラベス',
    'Whip': '鞭の音',
    'Scrape': 'こする音',
    'Scratch': 'ひっかく音',
    'Scratches': 'スクラッチノイズ',
    'Tap': 'タップ音',
    'Tick-tock': 'カチカチ音（時計）',
    'Tick': 'カチッという音',
    'Clicking': 'クリック音',
    'Clickety-clack': 'ガタンゴトン',
    'Bouncing': '跳ねる音',
    'Shake': '振る音',
    'Squeak': 'キーキー・チューチュー',
    'Creak': 'きしむ音',
    'Rustle': 'カサカサいう音',
    'Crackle': 'パチパチいう音',
    'Crushing': '砕ける音',
    'Crumpling, crinkling': 'くしゃくしゃにする音',
    'Tearing': '引き裂く音',
    'Shatter': '粉々になる音',
    'Ringtone': '着信音',
    'Telephone bell ringing': '電話のベル',
    'Alarm clock': '目覚まし時計',
    'Siren': 'サイレン',
    'Civil defense siren': '空襲警報',
    'Buzzer': 'ブザー',
    'Smoke detector, smoke alarm': '煙探知機',
    'Fire alarm': '火災報知器',
    'Foghorn': '霧笛',
    'Whistle': '笛',
    'Steam whistle': '汽笛',
    'Whoosh': 'ヒューという音',
    'Thump, thud': 'ドスンという音',
    'Thwack': 'ピシャリという音',
    'Smack, slap': '平手打ちの音',
    'Chink, clink': 'カチンという音',
    'Flap': 'はためく音',
    'Frying (food)': '揚げ物をする音',
    'Sizzle': 'ジュージューいう音',
    'Liquid': '液体',
    'Splash, splatter': '水しぶき',
    'Slosh': 'ザブザブいう音',
    'Squish': 'グチャッという音',
    'Drip': '滴る音',
    'Pour': '注ぐ音',
    'Trickle, dribble': 'ちょろちょろ流れる音',
    'Gurgling': 'ゴボゴボいう音',
    'Fill (with liquid)': '液体で満たす音',
    'Boiling': '沸騰する音',
    'Typing': 'タイピング',
    'Typewriter': 'タイプライター',
    'Computer keyboard': 'コンピュータのキーボード',
    'Writing': '筆記音',
    'Tap (dance)': 'タップダンス',
    'Swing (music)': 'スウィングジャズ',
    'Harmonica': 'ハーモニカ',
    'Accordion': 'アコーディオン',
    'Bagpipes': 'バグパイプ',
    'Didgeridoo': 'ディジュリドゥ',
    'Shofar': 'ショファー（角笛）',
    'Brass instrument': '金管楽器',
    'French horn': 'フレンチホルン',
    'Trumpet': 'トランペット',
    'Trombone': 'トロンボーン',
    'Tuba': 'チューバ',
    'Bowed string instrument': '擦弦楽器',
    'Violin, fiddle': 'ヴァイオリン',
    'Pizzicato': 'ピッツィカート',
    'Viola': 'ヴィオラ',
    'Cello': 'チェロ',
    'Double bass': 'コントラバス',
    'Wind instrument, woodwind instrument': '木管楽器',
    'Flute': 'フルート',
    'Clarinet': 'クラリネット',
    'Saxophone': 'サックス',
    'Oboe': 'オーボエ',
    'Bassoon': 'ファゴット',
    'Fixed-pitch instrument': '固定ピッチ楽器',
    'Celesta': 'チェレスタ',
    'Music box': 'オルゴール',
    'Bells': '鐘',
    'Chime': 'チャイム',
    'Church bell': '教会の鐘',
    'Jingle bell': 'ジングルベル',
    'Bicycle bell': '自転車のベル',
    'Tuning fork': '音叉',
    'Wind chime': '風鈴',
    'Change ringing (campanology)': 'チェンジリンギング',
    'Harmonic': 'ハーモニクス',
    'Musical scale': '音階',
    'Scale (music)': '音階',
    'Arpeggio': 'アルペジオ',
    'Melody': 'メロディ',
    'Song': '歌',
    'Vocal music': '声楽曲',
    'A capella': 'ア・カペラ',
    'Music genre': '音楽ジャンル',
    'Pop music': 'ポップミュージック',
    'Hip hop music': 'ヒップホップ',
    'Rock music': 'ロック',
    'Heavy metal': 'ヘヴィメタル',
    'Punk rock': 'パンクロック',
    'Grunge': 'グランジ',
    'Progressive rock': 'プログレッシブロック',
    'Rock and roll': 'ロックンロール',
    'Psychedelic rock': 'サイケデリックロック',
    'Rhythm and blues': 'リズム・アンド・ブルース',
    'Soul music': 'ソウルミュージック',
    'Reggae': 'レゲエ',
    'Country': 'カントリーミュージック',
    'Swing': 'スウィング',
    'Bluegrass': 'ブルーグラス',
    'Funk': 'ファンク',
    'Folk music': 'フォークミュージック',
    'Middle Eastern music': '中東の音楽',
    'Jazz': 'ジャズ',
    'Disco': 'ディスコ',
    'Classical music': 'クラシック音楽',
    'Opera': 'オペラ',
    'Electronic music': '電子音楽',
    'House music': 'ハウスミュージック',
    'Techno': 'テクノ',
    'Dubstep': 'ダブステップ',
    'Drum and bass': 'ドラムンベース',
    'Electronica': 'エレクトロニカ',
    'Electronic dance music': 'EDM',
    'Ambient music': 'アンビエントミュージック',
    'Trance music': 'トランスミュージック',
    'Music for children': '童謡',
    'New-age music': 'ニューエイジミュージック',
    'Vocal jazz': 'ヴォーカルジャズ',
    'Jingle (music)': 'ジングル',
    'Soundtrack music': 'サウンドトラック',
    'Film score': '映画音楽',
    'Video game music': 'ゲーム音楽',
    'Christmas music': 'クリスマス音楽',
    'Dance music': 'ダンスミュージック',
    'Wedding music': 'ウェディングミュージック',
    'Happy music': 'ハッピーな音楽',
    'Sad music': '悲しい音楽',
    'Tender music': '優しい音楽',
    'Exciting music': 'エキサイティングな音楽',
    'Angry music': '怒りの音楽',
    'Scary music': '怖い音楽',
    'Wind': '風の音',
    'Rustling leaves': '葉の擦れる音',
    'Wind noise (microphone)': 'マイクの風切り音',
    'Thunderstorm': '雷雨',
    'Thunder': '雷鳴',
    'Water': '水の音',
    'Rain': '雨',
    'Raindrop': '雨だれ',
    'Patter': 'パラパラ音',
    'Rain on surface': '雨が何かに当たる音',
    'Stream': '小川のせせらぎ',
    'Gurgle': 'ゴボゴボいう音',
    'Ocean': '海',
    'Waves, surf': '波',
    'Gush': '噴出する音',
    'Fire': '火',
    'Crackle (fire)': '火がパチパチいう音',
    'Vehicle': '乗り物',
    'Boat, Water vehicle': 'ボート・船',
    'Sailboat, sailing ship': '帆船',
    'Rowboat, canoe, kayak': '手漕ぎボート・カヌー',
    'Motorboat': 'モーターボート',
    'Vehicle horn, car horn, honking': 'クラクション',
    'Car': '自動車',
    'Vehicle engine': '乗り物のエンジン',
    'Engine starting': 'エンジン始動音',
    'Idling': 'アイドリング',
    'Engine': 'エンジン音',
    'Engine knocking': 'エンジンノッキング音',
    'Engine running': 'エンジン稼働音',
    'Engine accelerating, revving, vroom': 'エンジン加速音',
    'Truck': 'トラック',
    'Air brake': 'エアブレーキ',
    'Air horn, truck horn': 'エアホーン',
    'Reversing beeps': '後退時の警告音',
    'Bus': 'バス',
    'Race car, auto racing': 'レースカー',
    'Motorcycle': 'バイク',
    'Bicycle': '自転車',
    'Skateboard': 'スケートボード',
    'Train': '電車',
    'Train whistle': '汽笛（電車）',
    'Train horn': '電車の警笛',
    'Railroad car, train wagon': '貨車',
    'Train wheels squealing': '電車の車輪のきしみ音',
    'Subway, metro, underground': '地下鉄',
    'Aircraft': '航空機',
    'Aircraft engine': '航空機のエンジン',
    'Jet engine': 'ジェットエンジン',
    'Propeller, airscrew': 'プロペラ機',
    'Helicopter': 'ヘリコプター',
    'Fixed-wing aircraft, airplane': '飛行機',
    'Tools': '道具',
    'Hammer': 'ハンマー',
    'Jackhammer': '削岩機',
    'Sawing': 'のこぎり',
    'Filing (rasp)': 'やすり',
    'Sanding': 'サンディング',
    'Power tool': '電動工具',
    'Drill': 'ドリル',
    'Explosion': '爆発',
    'Gunshot, gunfire': '銃声',
    'Machine gun': 'マシンガン',
    'Fusillade': '一斉射撃',
    'Artillery fire': '砲撃',
    'Cap gun': 'おもちゃの銃',
    'Fireworks': '花火',
    'Firecracker': '爆竹',
    'Eruption': '噴火',
    'Boom': 'ドーンという音',
    'Wood': '木',
    'Chop': '叩き切る音',
    'Splinter': '木が裂ける音',
    'Glass': 'ガラス',
    'Chink, clink (glass)': 'ガラスがカチンと鳴る音',
    'Shatter (glass)': 'ガラスが割れる音',
    'Liquid (splash)': '液体（飛沫）',
    'Typing (computer)': 'タイピング（コンピュータ）',
    'Speech noise': '話し声ノイズ',
    'Inside, small room': '室内（小部屋）',
    'Inside, large room or hall': '室内（大部屋・ホール）',
    'Outside, urban or manmade': '屋外（都市・人工）',
    'Outside, rural or natural': '屋外（田舎・自然）',
    'Domestic sounds, home sounds': '生活音',
    'Bell': 'ベル',
    'Alarm': 'アラーム',
    'Telephone': '電話',
    'Telephone ringing': '電話の呼び出し音',
    'Mechanisms': '機械音',
    'Ratchet, pawl': 'ラチェット',
    'Clock': '時計',
    'Mechanical fan': '扇風機',
    'Printer': 'プリンター',
    'Camera': 'カメラ',
    'Single-lens reflex camera': '一眼レフカメラ',
    'Door': 'ドア',
    'Doorbell': 'ドアベル',
    'Door knocker': 'ドアノッカー',
    'Door lock, sign in, sign off': 'ドアの施錠・開錠音',
    'Cupboard open or close': '食器棚の開閉',
    'Squeal': 'キーキーいう音',
    'Vehicle (road)': '車両（道路）',
    'Car alarm': '自動車の警報',
    'Power windows, electric windows': 'パワーウィンドウ',
    'Skidding': 'スキッド音',
    'Tire squeal': 'タイヤのきしみ音',
    'Car passing by': '車が通り過ぎる音',
    'Rail transport': '鉄道輸送',
    'Air conditioning': 'エアコン',
    'Vacuum cleaner': '掃除機',
    'Zipper (clothing)': 'ジッパー',
    'Keys jangling': '鍵がじゃらじゃら鳴る音',
    'Coin (dropping)': 'コインが落ちる音',
    'Packing tape, duct tape': '梱包テープ',
    'Scissors': 'はさみ',
    'Typing on a computer keyboard': 'キーボードタイピング',
    'Microwave oven': '電子レンジ',
    'Blender': 'ミキサー',
    'Water tap, faucet': '蛇口',
    'Sink (filling or washing)': 'シンク（水張り・洗浄）',
    'Bathtub (filling or washing)': '浴槽（水張り・洗浄）',
    'Hair dryer': 'ヘアドライヤー',
    'Toilet flush': 'トイレを流す音',
    'Toothbrush': '歯ブラシ',
    'Electric toothbrush': '電動歯ブラシ',
    'Dishes, pots, and pans': '食器・鍋・フライパン',
    'Cutlery, silverware': 'カトラリー',
    'Chopping (food)': '食材を切る音',
    'Human group actions': '人間の集団行動',
    'Silence': '静寂',
    'Static': 'スタティックノイズ',
    'Mains hum': '電源ハムノイズ',
    'Noise': 'ノイズ',
    'Environmental noise': '環境ノイズ',
    'Background music': 'BGM',
    'Background noise': '背景雑音',
    'Sound effect': '効果音',
    'Pulse': 'パルス音',
    'Inside, public space': '屋内（公共空間）',
    'Shopping mall': 'ショッピングモール',
    'Airport': '空港',
    'Train station': '駅',
    'Bus station': 'バス停',
    'Street': '通り',
    'Alley': '路地',
    'Park': '公園',
    'Speech, human voice': '話し声・人の声',
    'Male speech, man speaking': '男性の話し声',
    'Female speech, woman speaking': '女性の話し声',
    'Boy': '少年の声',
    'Girl': '少女の声',
    'Man': '男性の声',
    'Woman': '女性の声',
    'Earmark': 'イヤーマーク（特定の音）',
    'Child speech': '子供の話し声',
    'Canidae, dogs, wolves': 'イヌ科',
    'Felidae, cats': 'ネコ科',
    'Bird, bird song': '鳥・さえずり',
    'Woodpecker': 'キツツキ',
    'Animal sounds': '動物の鳴き声',
    'Vehicle sounds': '乗り物の音',
    'Rail vehicles': '鉄道車両',
    'Motor vehicle (road)': '自動車（道路）',
    'Human sounds': '人間の出す音',
    'Respiratory sounds': '呼吸音',
    'Digestive': '消化音',
    'Body sounds': '体の音',
    'Human locomotion': '人の移動音',
    'Hands (sound)': '手の音',
    'Human voice': '人の声',
    'Vocal music, song': '声楽曲・歌',
    'Music (genre)': '音楽（ジャンル）',
    'Musical concepts': '音楽の概念',
    'Instrumental music': '器楽曲',
    'Sound reproduction': '音響再生',
    'Sound amplification': '音響増幅',
    'Sound recording': '録音',
    'Mechanical fan, fan': '扇風機',
    'Engine sounds': 'エンジン音',
    'Aircraft sounds': '航空機の音',
    'Surface contact': '表面接触音',
    'Deformation': '変形音',
    'Impact': '衝撃音',
    'Onomatopoeia': 'オノマトペ',
    'Alarm, siren': 'アラーム・サイレン',
    'Bell, chime': 'ベル・チャイム',
    'Domestic sounds': '生活音',
    'Kitchen sounds': '台所の音',
    'Bathroom sounds': '浴室の音',
    'Domestic appliances': '家電製品',
    'Miscellaneous sources': 'その他の音源',
    'Specific sounds': '特定の音',
    'Generic impact sounds': '一般的な衝撃音',
    'Surface contact (generic)': '一般的な表面接触音',
    'Sound events': '音響イベント',
    'Human-made sounds': '人工音',
    'Natural sounds': '自然音',
    'Source-ambiguous sounds': '音源不明な音',
    'Channel': 'チャンネル（音響）'
}

class SEDAggregator:
    """SED データ集計クラス"""
    
    def __init__(self):
        # Supabaseクライアントの初期化
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URLおよびSUPABASE_KEYが設定されていません")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.time_slots = self._generate_time_slots()
        print(f"✅ Supabase接続設定完了")

    def _translate_event_name(self, event_name: str) -> str:
        """イベント名を日本語に翻訳する（音の統合も適用）"""
        # まず統合マッピングをチェック
        if event_name in SOUND_CONSOLIDATION:
            return SOUND_CONSOLIDATION[event_name]
        # 次に通常の翻訳マッピングをチェック
        return AUDIOSET_LABEL_MAP.get(event_name, event_name) # マップにない場合は元の名前を返す
    
    def _generate_time_slots(self) -> List[str]:
        """30分スロットのリストを生成（00-00 から 23-30 まで）"""
        slots = []
        for hour in range(24):
            for minute in [0, 30]:
                slots.append(f"{hour:02d}-{minute:02d}")
        return slots
    
    async def fetch_all_data(self, device_id: str, date: str) -> Dict[str, List[Dict]]:
        """指定日の全SEDデータをSupabaseから取得"""
        print(f"📊 Supabaseからデータ取得開始: device_id={device_id}, date={date}")
        
        try:
            # Supabaseからデータを取得
            response = self.supabase.table('behavior_yamnet').select('*').eq(
                'device_id', device_id
            ).eq(
                'date', date
            ).execute()
            
            # 結果をtime_blockごとに整理
            results = {}
            for row in response.data:
                time_block = row['time_block']
                events = row['events']  # jsonb型なのでそのまま辞書として扱える
                results[time_block] = events
            
            print(f"✅ データ取得完了: {len(results)}/{len(self.time_slots)} スロット")
            return results
            
        except Exception as e:
            print(f"❌ Supabaseからのデータ取得エラー: {e}")
            return {}
    
    def _extract_events_from_supabase(self, events_data: List[Dict]) -> List[str]:
        """Supabaseのeventsカラムから音響イベントラベルを抽出（新形式対応）
        
        除外リスト（EXCLUDED_EVENTS）に含まれるイベントは自動的にフィルタリングされます。
        """
        events = []
        
        # デバッグ: データ形式を確認
        if events_data and len(events_data) > 0:
            first_item = events_data[0]
            # 旧形式チェック: {"label": "xxx", "prob": 0.xx}
            if 'label' in first_item and 'prob' in first_item:
                # 旧形式の処理
                for event in events_data:
                    if isinstance(event, dict) and 'label' in event:
                        label = event['label']
                        # 除外リストに含まれていないイベントのみ追加
                        if label not in EXCLUDED_EVENTS:
                            events.append(label)
            # 新形式チェック: {"time": 0.0, "events": [...]}
            elif 'time' in first_item and 'events' in first_item:
                # 新形式の処理
                for time_block in events_data:
                    if isinstance(time_block, dict) and 'events' in time_block:
                        for event in time_block['events']:
                            if isinstance(event, dict) and 'label' in event:
                                label = event['label']
                                # 除外リストに含まれていないイベントのみ追加
                                if label not in EXCLUDED_EVENTS:
                                    events.append(label)
        
        return events
    
    def _create_summary_ranking(self, all_events: List[str]) -> List[Dict[str, int]]:
        """優先順位に基づいて生活音リストを作成（最大10件）"""
        counter = Counter(all_events)
        result = []
        used_events = set()
        
        # 優先度1: 生体反応（全て含める）
        for event in PRIORITY_CATEGORIES['biometric']:
            if event in counter and event not in used_events:
                translated_event = self._translate_event_name(event)
                result.append({"event": translated_event, "count": counter[event]})
                used_events.add(event)
        
        # 優先度2: 声・会話（残り枠に入れる）
        if len(result) < 10:
            voice_events = []
            for event in PRIORITY_CATEGORIES['voice']:
                if event in counter and event not in used_events:
                    voice_events.append((event, counter[event]))
            # 声関連は出現回数順でソート
            voice_events.sort(key=lambda x: x[1], reverse=True)
            for event, count in voice_events:
                if len(result) >= 10:
                    break
                translated_event = self._translate_event_name(event)
                result.append({"event": translated_event, "count": count})
                used_events.add(event)
        
        # 優先度3: 生活音（残り枠に入れる）
        if len(result) < 10:
            daily_events = []
            for event in PRIORITY_CATEGORIES['daily_life']:
                if event in counter and event not in used_events:
                    daily_events.append((event, counter[event]))
            # 生活音も出現回数順でソート
            daily_events.sort(key=lambda x: x[1], reverse=True)
            for event, count in daily_events:
                if len(result) >= 10:
                    break
                translated_event = self._translate_event_name(event)
                result.append({"event": translated_event, "count": count})
                used_events.add(event)
        
        # 優先度4: その他（残り枠に入れる）
        if len(result) < 10:
            other_events = []
            for event, count in counter.items():
                if event not in used_events:
                    other_events.append((event, count))
            # その他も出現回数順でソート
            other_events.sort(key=lambda x: x[1], reverse=True)
            for event, count in other_events:
                if len(result) >= 10:
                    break
                translated_event = self._translate_event_name(event)
                result.append({"event": translated_event, "count": count})
                used_events.add(event)
        
        return result
    
    def _create_time_blocks(self, slot_data: Dict[str, List[Dict]]) -> Dict[str, Optional[List[Dict[str, Any]]]]:
        """スロット別のイベント集計を構造化形式で作成"""
        time_blocks = {}
        
        for slot in self.time_slots:
            if slot in slot_data:
                events = self._extract_events_from_supabase(slot_data[slot])
                if events:
                    counter = Counter(events)
                    # イベントを構造化形式で表現
                    event_list = []
                    for event, count in counter.most_common():
                        translated_event = self._translate_event_name(event)
                        event_list.append({"event": translated_event, "count": count})
                    time_blocks[slot] = event_list
                else:
                    # データは存在するがイベントが空の場合
                    time_blocks[slot] = []
            else:
                # データが存在しない場合はnull
                time_blocks[slot] = None
        
        return time_blocks
    
    def aggregate_data(self, slot_data: Dict[str, List[Dict]]) -> Dict:
        """収集したデータを集計して結果形式を生成"""
        print("📊 データ集計開始...")
        
        # 全イベントを収集
        all_events = []
        for events_data in slot_data.values():
            events = self._extract_events_from_supabase(events_data)
            all_events.extend(events)
        
        # summary_ranking作成
        summary_ranking = self._create_summary_ranking(all_events)
        
        # time_blocks作成
        time_blocks = self._create_time_blocks(slot_data)
        
        result = {
            "summary_ranking": summary_ranking,
            "time_blocks": time_blocks
        }
        
        print(f"✅ 集計完了: 総イベント数 {len(all_events)}")
        return result
    
    async def save_to_supabase(self, result: Dict, device_id: str, date: str) -> bool:
        """結果をSupabaseのbehavior_summaryテーブルに保存"""
        try:
            # Supabaseにデータを保存（UPSERT）
            response = self.supabase.table('behavior_summary').upsert({
                'device_id': device_id,
                'date': date,
                'summary_ranking': result['summary_ranking'],
                'time_blocks': result['time_blocks']
            }).execute()
            
            print(f"💾 Supabase保存完了: behavior_summary テーブル")
            print(f"   device_id: {device_id}, date: {date}")
            return True
            
        except Exception as e:
            print(f"❌ Supabase保存エラー: {e}")
            return False
    
    async def run(self, device_id: str, date: str) -> dict:
        """メイン処理実行"""
        print(f"🚀 SED集計処理開始: {device_id}, {date}")
        
        # Supabaseからデータ取得
        slot_data = await self.fetch_all_data(device_id, date)
        
        if not slot_data:
            print(f"⚠️ {date}のデータがありません")
            return {"success": False, "reason": "no_data", "message": f"{date}のデータがありません"}
        
        # データ集計
        result = self.aggregate_data(slot_data)
        
        # Supabaseに保存
        success = await self.save_to_supabase(result, device_id, date)
        
        if success:
            print("🎉 SED集計処理完了")
            return {"success": True, "message": "処理完了"}
        else:
            return {"success": False, "reason": "save_error", "message": "データの保存に失敗しました"}


async def main():
    """コマンドライン実行用メイン関数"""
    parser = argparse.ArgumentParser(description="SED データ集計ツール (Supabase版)")
    parser.add_argument("device_id", help="デバイスID（例: d067d407-cf73-4174-a9c1-d91fb60d64d0）")
    parser.add_argument("date", help="対象日付（YYYY-MM-DD形式）")
    
    args = parser.parse_args()
    
    # 日付形式検証
    try:
        datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        print("❌ エラー: 日付はYYYY-MM-DD形式で指定してください")
        return
    
    # 集計実行
    aggregator = SEDAggregator()
    result = await aggregator.run(args.device_id, args.date)
    
    if result["success"]:
        print(f"\n✅ 処理完了")
        print(f"💾 データはSupabaseのbehavior_summaryテーブルに保存されました")
    else:
        print(f"\n❌ 処理失敗: {result['message']}")


if __name__ == "__main__":
    asyncio.run(main())