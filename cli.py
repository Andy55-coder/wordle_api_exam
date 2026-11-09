import sys
import os
import pygame
import requests

# API 設定（指向你的 Render 雲端網址）
API_BASE_URL = "https://wordle-api-exam.onrender.com"

# 顏色定義
COLOR_BG = (18, 18, 19)
COLOR_PANEL_BG = (28, 28, 30)
COLOR_TEXT = (255, 255, 255)
COLOR_TEXT_MUTED = (160, 160, 165)
COLOR_EMPTY = (18, 18, 19)
COLOR_BORDER_EMPTY = (58, 58, 60)
COLOR_BORDER_FILLED = (117, 113, 94)
COLOR_CORRECT = (83, 141, 78)    # 綠色
COLOR_PRESENT = (181, 159, 59)  # 黃色
COLOR_ABSENT = (58, 58, 60)      # 灰色

pygame.init()
WIDTH, HEIGHT = 700, 650  # 任務三：將寬度從 500 擴大為 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pygame Wordle + FastAPI Client")

def get_font(size, bold=False):
    for name in ["Arial", "Microsoft JhengHei", "sans-serif"]:
        try:
            return pygame.font.SysFont(name, size, bold=bold)
        except:
            continue
    return pygame.font.Font(None, size)

title_font = get_font(24, bold=True)
font = get_font(32, bold=True)
sub_font = get_font(14, bold=True)
small_font = get_font(13)

class WordleGame:
    def __init__(self):
        self.game_id = None
        self.grid = [["" for _ in range(5)] for _ in range(6)]
        self.colors = [[COLOR_EMPTY for _ in range(5)] for _ in range(6)]
        self.border_colors = [[COLOR_BORDER_EMPTY for _ in range(5)] for _ in range(6)]
        self.row = 0
        self.col = 0
        self.game_over = False
        self.loading = False
        self.hard_mode = False  # 任務四：硬核模式開關
        self.message = "Press ENTER to submit, R to restart, H for Hard Mode"
        
        # 任務三統計數據
        self.total_games = 0
        self.wins = 0
        self.win_rate = 0.0
        self.guess_history = []  # 側邊欄歷史紀錄 [{"guess": "...", "feedback": [...]}, ...]

        self.start_new_game()

    def fetch_stats(self):
        """任務三：取得後端勝率統計"""
        try:
            res = requests.get(f"{API_BASE_URL}/api/stats", timeout=5)
            if res.status_code == 200:
                data = res.json()
                self.total_games = data["total_games"]
                self.wins = data["wins"]
                self.win_rate = data["win_rate"]
        except:
            pass

    def start_new_game(self):
        """任務四：支援 hard_mode 參數重新開局"""
        self.loading = True
        self.message = "Connecting to server..."
        pygame.event.pump() 

        try:
            res = requests.post(f"{API_BASE_URL}/api/new-game?hard_mode={str(self.hard_mode).lower()}", timeout=30)
            if res.status_code == 200:
                data = res.json()
                self.game_id = data["game_id"]
                self.grid = [["" for _ in range(5)] for _ in range(6)]
                self.colors = [[COLOR_EMPTY for _ in range(5)] for _ in range(6)]
                self.border_colors = [[COLOR_BORDER_EMPTY for _ in range(5)] for _ in range(6)]
                self.row = 0
                self.col = 0
                self.game_over = False
                self.guess_history = []
                mode_str = "HARD" if self.hard_mode else "Normal"
                self.message = f"New game started! Mode: {mode_str}"
                self.fetch_stats()
            else:
                self.message = "Server error starting new game."
        except requests.exceptions.RequestException:
            self.message = "Cannot connect to FastAPI server!"
        finally:
            self.loading = False

    def submit_guess(self):
        """任務一、二：提交單字並處理伺服器回應"""
        if self.col < 5:
            self.message = "Not enough letters!"
            return

        guess_word = "".join(self.grid[self.row])
        self.loading = True
        self.message = "Verifying guess..."

        try:
            payload = {"game_id": self.game_id, "guess": guess_word}
            res = requests.post(f"{API_BASE_URL}/api/guess", json=payload, timeout=30)
            
            if res.status_code == 200:
                data = res.json()
                feedback = data["feedback"]
                is_correct = data["is_correct"]
                is_game_over = data["is_game_over"]
                attempts_left = data["attempts_left"]
                target_word = data.get("target_word")
                
                # 更新當前行格子顏色
                for i in range(5):
                    if feedback[i] == "correct":
                        self.colors[self.row][i] = COLOR_CORRECT
                        self.border_colors[self.row][i] = COLOR_CORRECT
                    elif feedback[i] == "present":
                        self.colors[self.row][i] = COLOR_PRESENT
                        self.border_colors[self.row][i] = COLOR_PRESENT
                    else:
                        self.colors[self.row][i] = COLOR_ABSENT
                        self.border_colors[self.row][i] = COLOR_ABSENT

                # 記錄至側邊欄歷史紀錄
                self.guess_history.append({"guess": guess_word, "feedback": feedback})

                if is_correct:
                    self.message = "Congratulations! You won! Press R to restart."
                    self.game_over = True
                    self.fetch_stats()
                elif is_game_over:
                    # 任務一：6次機會用盡顯示正確答案
                    self.message = f"Game Over! The word was {target_word}. Press R to restart."
                    self.game_over = True
                    self.fetch_stats()
                else:
                    # 任務一：每次猜測後顯示剩餘次數
                    self.row += 1
                    self.col = 0
                    self.message = f"Keep guessing! ({attempts_left} tries left)"
            else:
                err_detail = res.json().get("detail", "Error")
                # 任務二：單字不在字典中時處理
                if err_detail == "Word not in dictionary" or "Hard Mode" in err_detail:
                    self.message = "Not not in word list!" if err_detail == "Word not in dictionary" else err_detail
                    # 任務二關鍵：身體不消耗猜測次數（row 不增加，玩家可按 Backspace 修改）
                else:
                    self.message = err_detail
        except requests.exceptions.RequestException:
            self.message = "Network error during guess!"
        finally:
            self.loading = False

    def handle_keydown(self, event):
        if self.loading:
            return

        # 任務四：按下 H 鍵切換硬核模式並重新開局
        if event.key == pygame.K_h:
            self.hard_mode = not self.hard_mode
            self.start_new_game()
            return

        if event.key == pygame.K_r:
            self.start_new_game()
            return

        if self.game_over:
            return

        if event.key == pygame.K_BACKSPACE:
            if self.col > 0:
                self.col -= 1
                self.grid[self.row][self.col] = ""
                self.border_colors[self.row][self.col] = COLOR_BORDER_EMPTY
        elif event.key == pygame.K_RETURN:
            self.submit_guess()
        elif event.unicode.isalpha() and len(event.unicode) == 1:
            if self.col < 5:
                self.grid[self.row][self.col] = event.unicode.upper()
                self.border_colors[self.row][self.col] = COLOR_BORDER_FILLED
                self.col += 1

    def draw(self, surface):
        surface.fill(COLOR_BG)
        
        # 1. 左側主遊戲區標題與模式顯示
        title_surf = title_font.render("WORDLE", True, COLOR_TEXT)
        surface.blit(title_surf, (30, 20))

        # 任務四：畫面右上角顯示目前模式
        mode_text = f"Mode: {'HARD' if self.hard_mode else 'Normal'}"
        mode_color = (231, 76, 60) if self.hard_mode else (46, 204, 113)
        mode_surf = sub_font.render(mode_text, True, mode_color)
        surface.blit(mode_surf, (470 - mode_surf.get_width(), 25))

        pygame.draw.line(surface, (40, 40, 42), (20, 55), (480, 55), 1)

        # 2. 繪製 6x5 遊戲網格
        box_size = 50
        gap = 8
        margin_x = 35
        margin_y = 70

        for r in range(6):
            for c in range(5):
                x = margin_x + c * (box_size + gap)
                y = margin_y + r * (box_size + gap)
                rect = pygame.Rect(x, y, box_size, box_size)
                
                pygame.draw.rect(surface, self.colors[r][c], rect, border_radius=4)
                border_color = self.border_colors[r][c]
                pygame.draw.rect(surface, border_color, rect, width=2, border_radius=4)

                char = self.grid[r][c]
                if char:
                    text_surface = font.render(char, True, COLOR_TEXT)
                    text_rect = text_surface.get_rect(center=rect.center)
                    surface.blit(text_surface, text_rect)

        # 3. 任務三：右側區域 (x: 500-700) 繪製分隔線與歷史紀錄面板
        pygame.draw.line(surface, (60, 60, 65), (500, 20), (500, HEIGHT - 70), 2)
        
        # 側邊欄上方勝率統計顯示
        stats_box = pygame.Rect(515, 20, 170, 65)
        pygame.draw.rect(surface, COLOR_PANEL_BG, stats_box, border_radius=6)
        
        stat_title = sub_font.render("STATISTICS", True, COLOR_TEXT)
        stat_content = small_font.render(f"Total: {self.total_games} | Wins: {self.wins}", True, COLOR_TEXT_MUTED)
        rate_content = small_font.render(f"Win Rate: {self.win_rate}%", True, COLOR_TEXT_MUTED)
        
        surface.blit(stat_title, (stats_box.x + 10, stats_box.y + 8))
        surface.blit(stat_content, (stats_box.x + 10, stats_box.y + 28))
        surface.blit(rate_content, (stats_box.x + 10, stats_box.y + 45))

        # 歷史紀錄列表
        history_title = sub_font.render("GUESS HISTORY", True, COLOR_TEXT)
        surface.blit(history_title, (515, 100))

        hx, hy = 515, 125
        for item in self.guess_history:
            guess_word = item["guess"]
            feedback = item["feedback"]
            
            # 繪製單字的小色塊預覽
            sub_box_size = 22
            sub_gap = 4
            for i, char in enumerate(guess_word):
                sb_rect = pygame.Rect(hx + i * (sub_box_size + sub_gap), hy, sub_box_size, sub_box_size)
                
                # 對應顏色
                c_bg = COLOR_ABSENT
                if feedback[i] == "correct":
                    c_bg = COLOR_CORRECT
                elif feedback[i] == "present":
                    c_bg = COLOR_PRESENT
                
                pygame.draw.rect(surface, c_bg, sb_rect, border_radius=3)
                char_surf = small_font.render(char, True, COLOR_TEXT)
                char_rect = char_surf.get_rect(center=sb_rect.center)
                surface.blit(char_surf, char_rect)
            
            hy += 30

        # 4. 底部訊息提示列
        msg_surface = small_font.render(self.message, True, COLOR_TEXT)
        surface.blit(msg_surface, (35, HEIGHT - 35))


def main():
    clock = pygame.time.Clock()
    game = WordleGame()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                game.handle_keydown(event)

        game.draw(screen)
        pygame.display.flip()
        clock.tick(30)

if __name__ == "__main__":
    main()
