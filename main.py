import os
import random
import uuid
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Wordle API Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

WORD_BANK = [
    "APPLE", "TRAIN", "HOUSE", "PLANT", "SMART", "WORLD", "LIGHT", "BRAIN", "CLOUD", "WATER",
    "ABOUT", "ABOVE", "ACTOR", "ACUTE", "ADMIT", "ADOPT", "ADULT", "AFTER", "AGAIN", "AGENT",
    "AGREE", "AHEAD", "ALARM", "ALBUM", "ALERT", "ALIEN", "ALIKE", "ALIVE", "ALLOW", "ALONE",
    "ALONG", "ALTER", "AMONG", "ANGER", "ANGLE", "ANGRY", "APART", "APPLY", "ARGUE", "ARISE",
    "ARRAY", "ARROW", "ASIDE", "ASSET", "AUDIO", "AUDIT", "AVOID", "AWAKE", "AWARE", "BADGE",
    "BAKER", "BASIC", "BASIS", "BEACH", "BEGIN", "BEING", "BELOW", "BENCH", "BLACK", "BLAME",
    "BLANK", "BLAST", "BLEED", "BLEND", "BLOCK", "BLOOD", "BOARD", "BOAST", "BONUS", "BOOST",
    "BOUND", "BREAD", "BREAK", "BRICK", "BRIEF", "BRING", "BROAD", "BROWN", "BRUSH", "BUILD",
    "BUNCH", "BUYER", "CABLE", "CANDY", "CARGO", "CARRY", "CATCH", "CAUSE", "CHAIN", "CHAIR",
    "CHALK", "CHARM", "CHART", "CHASE", "CHEAP", "CHECK", "CHEST", "CHIEF", "CHILD", "CHOSE",
    "CIVIL", "CLAIM", "CLASS", "CLEAN", "CLEAR", "CLIMB", "CLOCK", "CLOSE", "COACH", "COAST",
    "COUNT", "COURT", "COVER", "CRASH", "CREAM", "CRIME", "CROSS", "CROWD", "CROWN", "CURVE",
    "CYCLE", "DAILY", "DANCE", "DEATH", "DELAY", "DEPTH", "DRAFT", "DRAMA", "DREAM", "DRIVE",
    "EAGLE", "EARLY", "EARTH", "EIGHT", "EMPTY", "ENEMY", "ENJOY", "ENTER", "EQUAL", "ERROR",
    "EVENT", "EVERY", "EXACT", "EXIST", "FAITH", "FALSE", "FAULT", "FIELD", "FIGHT", "FINAL",
    "FIRST", "FLAME", "FLASH", "FLOAT", "FLOOR", "FLOUR", "FLUID", "FOCUS", "FORCE", "FORTH",
    "FORTY", "FORUM", "FRAME", "FRESH", "FRONT", "FRUIT", "GIANT", "GLASS", "GLOBE", "GRACE",
    "GRADE", "GRAND", "GRANT", "GRASS", "GREAT", "GREEN", "GROUP", "GUARD", "GUESS", "GUIDE",
    "HAPPY", "HEART", "HEAVY", "HOTEL", "HUMAN", "IMAGE", "INDEX", "INPUT", "ISSUE", "JUDGE",
    "KNIFE", "LAYER", "LEMON", "LEVEL", "LIMIT", "LUNCH", "MAGIC", "MAJOR", "MARCH", "MATCH",
    "MEDAL", "MONEY", "MONTH", "MUSIC", "NIGHT", "NOVEL", "NURSE", "OCEAN", "OFFER", "ORDER"
]

# 遊戲狀態儲存
games_db: Dict[str, dict] = {}

# 任務三：全域勝率統計數據
global_stats = {
    "total_games": 0,
    "wins": 0
}

class GuessRequest(BaseModel):
    game_id: str
    guess: str


@app.post("/api/new-game")
def start_new_game(hard_mode: bool = Query(False)):
    """任務一與四：建立新遊戲，支援 hard_mode 參數"""
    global_stats["total_games"] += 1
    
    game_id = str(uuid.uuid4())
    target_word = random.choice(WORD_BANK)
    games_db[game_id] = {
        "target": target_word,
        "status": "PLAYING",
        "hard_mode": hard_mode,
        "attempts": 0,
        "history": [],  # 記錄已猜過的資訊供 Hard Mode 檢查
        "revealed_correct": {}  # 紀錄位置固定正確的字母 {index: char}
    }
    return {"game_id": game_id, "message": "New game started!", "hard_mode": hard_mode}


@app.get("/api/stats")
def get_stats():
    """任務三：取得勝率統計 API"""
    total = global_stats["total_games"]
    wins = global_stats["wins"]
    win_rate = round((wins / total * 100), 1) if total > 0 else 0.0
    return {
        "total_games": total,
        "wins": wins,
        "win_rate": win_rate
    }


@app.post("/api/guess")
def process_guess(req: GuessRequest):
    """任務一、二、四：驗證猜測、單字檢查、硬核模式判定"""
    game_id = req.game_id
    guess = req.guess.strip().upper()

    if game_id not in games_db:
        raise HTTPException(status_code=404, detail="Game session not found.")
    
    if len(guess) != 5 or not guess.isalpha():
        raise HTTPException(status_code=400, detail="Word must be 5 letters.")

    # 任務二：檢查單字是否在字典中
    if guess not in WORD_BANK:
        raise HTTPException(status_code=400, detail="Word not in dictionary")

    game_data = games_db[game_id]
    target = game_data["target"]
    hard_mode = game_data["hard_mode"]
    revealed_correct = game_data["revealed_correct"]

    # 任務四：硬核模式驗證（必須維持先前確認為綠色的字母與位置）
    if hard_mode:
        for idx, char in revealed_correct.items():
            if guess[idx] != char:
                raise HTTPException(
                    status_code=400, 
                    detail="Hard Mode: Must use revealed hint at green position"
                )

    feedback = ["absent"] * 5
    target_letter_counts = {}

    for char in target:
        target_letter_counts[char] = target_letter_counts.get(char, 0) + 1

    # 1. 標記綠色 correct
    for i in range(5):
        if guess[i] == target[i]:
            feedback[i] = "correct"
            target_letter_counts[guess[i]] -= 1
            revealed_correct[i] = guess[i]  # 記錄硬核模式提示

    # 2. 標記黃色 present
    for i in range(5):
        if feedback[i] != "correct" and guess[i] in target:
            if target_letter_counts.get(guess[i], 0) > 0:
                feedback[i] = "present"
                target_letter_counts[guess[i]] -= 1

    game_data["attempts"] += 1
    game_data["history"].append({"guess": guess, "feedback": feedback})

    is_correct = (guess == target)
    is_game_over = is_correct or (game_data["attempts"] >= 6)

    if is_correct:
        game_data["status"] = "WON"
        global_stats["wins"] += 1

    # 任務一：如果是第 6 次猜錯或贏了，回傳 target_word；否則回傳 None
    response_target = target if is_game_over else None

    return {
        "guess": guess,
        "feedback": feedback,
        "is_correct": is_correct,
        "is_game_over": is_game_over,
        "target_word": response_target,
        "attempts_left": 6 - game_data["attempts"]
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
