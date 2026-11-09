import sys
import os
import pygame
import requests

# API 設定
API_BASE_URL = "https://wordle-api-exam.onrender.com"

# 顏色定義（現代質感深色風格）
COLOR_BG = (18, 18, 19)
COLOR_PANEL_BG = (28, 28, 30)       # 區塊背景色
COLOR_TEXT = (255, 255, 255)
COLOR_TEXT_MUTED = (160, 160, 165)  # 次要文字顏色
COLOR_EMPTY = (18, 18, 19)          # 內裝空白時的深色
COLOR_BORDER_EMPTY = (58, 58, 60)   # 未輸入時的邊框灰色
COLOR_BORDER_FILLED = (117, 113, 94) # 已輸入字元時的邊框
COLOR_CORRECT = (83, 141, 78)       # 綠色
COLOR_PRESENT = (181, 159, 59)     # 黃色
COLOR_ABSENT = (58, 58, 60)         # 灰色

pygame.init()
WIDTH, HEIGHT = 520, 740  # 稍微加大視窗以容納擴充的面板
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pygame Wordle + FastAPI Client (Expanded)")

# 設定具備防呆機制的字型
def get_font(size, bold=False):
    for name in ["Arial", "Microsoft JhengHei", "sans-serif"]:
        try:
            return pygame.font.SysFont(name, size, bold=bold)
        except:
            continue
    return pygame.font.Font(None, size)

title_font = get_font(28, bold=True)
font = get_font(34, bold=True)
sub_font = get_font(15, bold=True)
small_font = get_font(14)

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
        self.message = "Press ENTER to submit, R to restart"
        self.start_new_game()

    def start_new_game(self):
        """向 FastAPI 伺服器請求建立新的一局"""
        self.loading = True
        self.message = "Connecting to server ( waking up )..."
        pygame.event.pump() 

        try:
            res = requests.post(f"{API_BASE_URL}/api/new-game", timeout=30)
            if res.status_code == 200:
                data = res.json()
                self.game_id = data["game_id"]
                self.grid = [["" for _ in range(5)] for _ in range(6)]
                self.colors = [[COLOR_EMPTY for _ in range(5)] for _ in range(6)]
                self.border_colors = [[COLOR_BORDER_EMPTY for _ in range(5)] for _ in range(6)]
                self.row = 0
                self.col = 0
                self.game_over = False
                self.message = "New game started! Good luck!"
            else:
                self.message = "Server error starting new game."
        except requests.exceptions.RequestException:
            self.message = "Cannot connect to FastAPI server!"
        finally:
            self.loading = False

    def submit_guess(self):
        """將當前行單字發送至 FastAPI 驗證"""
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
                
                # 依據後端回傳更新格子顏色
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

                if data["is_correct"]:
                    self.message = "Congratulations! You won! Press R to restart."
                    self.game_over = True
                else:
                    self.row += 1
                    self.col = 0
                    if self.row == 6:
                        target = data.get("target_word", "SECRET")
                        self.message = f"Game Over! Answer: {target}. Press R."
                        self.game_over = True
                    else:
                        self.message = "Keep guessing!"
            else:
                self.message = res.json().get("detail", "Error processing guess")
        except requests.exceptions.RequestException:
            self.message = "Network error during guess!"
        finally:
            self.loading = False

    def handle_keydown(self, event):
        if self.loading:
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
        
        # 1. 頂部主標題與狀態面板
        title_surf = title_font.render("WORDLE CHALLENGE", True, COLOR_TEXT)
        title_rect = title_surf.get_rect(center=(WIDTH // 2, 30))
        surface.blit(title_surf, title_rect)
        
        # 狀態面板（顯示目前嘗試次數與 Session 簡碼）
        panel_rect = pygame.Rect(30, 60, WIDTH - 60, 45)
        pygame.draw.rect(surface, COLOR_PANEL_BG, panel_rect, border_radius=6)
        
        attempts_text = f"Attempts: {self.row}/6"
        id_text = f"Session: {self.game_id[:8]}..." if self.game_id else "Session: Connecting..."
        
        att_surf = sub_font.render(attempts_text, True, COLOR_TEXT_MUTED)
        id_surf = sub_font.render(id_text, True, COLOR_TEXT_MUTED)
        
        surface.blit(att_surf, (panel_rect.x + 15, panel_rect.y + 13))
        surface.blit(id_surf, (panel_rect.right - id_surf.get_width() - 15, panel_rect.y + 13))

        # 2. 繪製 6x5 遊戲網格（置中配置）
        box_size = 56
        gap = 8
        grid_width = 5 * box_size + 4 * gap
        margin_x = (WIDTH - grid_width) // 2
        margin_y = 130

        for r in range(6):
            for c in range(5):
                x = margin_x + c * (box_size + gap)
                y = margin_y + r * (box_size + gap)
                rect = pygame.Rect(x, y, box_size, box_size)
                
                # 畫方格背景與邊框
                pygame.draw.rect(surface, self.colors[r][c], rect, border_radius=4)
                border_color = self.border_colors[r][c]
                pygame.draw.rect(surface, border_color, rect, width=2, border_radius=4)

                # 畫字母
                char = self.grid[r][c]
                if char:
                    text_surface = font.render(char, True, COLOR_TEXT)
                    text_rect = text_surface.get_rect(center=rect.center)
                    surface.blit(text_surface, text_rect)

        # 3. 底部操作提示與訊息面板
        info_panel = pygame.Rect(30, 560, WIDTH - 60, 110)
        pygame.draw.rect(surface, COLOR_PANEL_BG, info_panel, border_radius=8)
        
        # 提示標題
        tip_title = sub_font.render("CONTROLS & STATUS", True, COLOR_TEXT)
        surface.blit(tip_title, (info_panel.x + 15, info_panel.y + 12))
        
        # 操作說明項目
        tips = [
            "• Type letters to fill row",
            "• Press [ENTER] to submit guess",
            "• Press [R] to restart a new game"
        ]
        for idx, tip in enumerate(tips):
            t_surf = small_font.render(tip, True, COLOR_TEXT_MUTED)
            surface.blit(t_surf, (info_panel.x + 15, info_panel.y + 38 + (idx * 20)))

        # 4. 最下方即時訊息列
        msg_surface = small_font.render(self.message, True, COLOR_TEXT)
        msg_rect = msg_surface.get_rect(center=(WIDTH // 2, HEIGHT - 25))
        surface.blit(msg_surface, msg_rect)


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
