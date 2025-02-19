import pygame
import time
import librosa
import math
import glob
import win11toast
import os
import random

songI = 0

def cycleSong(delta=0.22, pre_max=10.5, post_max=10.5):
    global songI
    audio_path = sorted(glob.glob("songs/*.MP3"))[songI]
    pygame.display.set_caption("Beat Rhythm - waiting")
    
    
    print("Audio file loading...")
    y, sr = librosa.load(audio_path, sr=None)
    onset_frames = librosa.onset.onset_detect(y=y, sr=sr, delta=delta, pre_max=pre_max, post_max=post_max, backtrack=True)
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)  # Onset times in seconds

    # Calculate song duration and set end trigger
    print("Calculating song duration...")
    song_duration = librosa.get_duration(y=y, sr=sr)
    end_trigger_time = song_duration - 10  # 10 seconds before song ends

    songI += 1
    if songI > len(glob.glob("songs/*.MP3")):  # Change the number of song when needed
        songI = 0
    pygame.display.set_caption(f"Beat Rhythm - {os.path.basename(audio_path)}")
    return end_trigger_time, onset_times, audio_path, song_duration

if not os.path.exists("songs"):
    os.mkdir("songs")

if len(glob.glob("songs/*.MP3")) == 0:
    win11toast.toast("Beat Rhythm - no songs available", "please add songs by adding them to songs folder")
    exit()

# Colors
WHITE = (255, 255, 255)
LIGHT_GRAY = (127, 127, 127)
GRAY = (100, 100, 100)
DARK_GRAY = (15, 15, 15)
BLACK = (0, 0, 0)

RED = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)

DARK_RED = (127, 0, 0)
DARK_GREEN = (0, 127, 0)
DARK_YELLOW = (127, 127, 0)
DARK_BLUE = (0, 0, 127)

# Initialize pygame
pygame.init()
screen = pygame.display.set_mode((800, 600))
print("processing song...")
end_trigger_time, onset_times, audio_path, song_duration = cycleSong()
print("song processed")
# Target zone settings
target_y = 550
target_radius = 30
target0_color = GREEN
target1_color = YELLOW
target2_color = BLUE
score = 0
maxScore = 0

score_font = pygame.font.Font(None, 36)
end_font = pygame.font.Font(None, 48)  # Font for end screen text
combo_multiplier_font = pygame.font.Font(None, 45)
targets_font = pygame.font.Font(None, 25)

score_color = WHITE
score_color_cooldown = 0
end_screen = False  # Variable to track if end screen should be displayed

targets_active = []
difficulty = "normal"
if difficulty == "easy":
    tolerance = 50
    beat_speed = 80
    targets_active = [0]
    max_combo_multiplier = 15
elif difficulty == "normal":
    tolerance = 40
    beat_speed = 155  # Speed at which onsets move down the screen (pixels per second)
    targets_active = [-1, 1]
    max_combo_multiplier = 10
elif difficulty == "hard":
    tolerance = 40  # Narrow tolerance for harder mode
    beat_speed = 200
    targets_active = [-1, 0, 1]
    max_combo_multiplier = 7
elif difficulty == "extreme":
    tolerance = 35  # Narrow tolerance for harder mode
    beat_speed = 230
    targets_active = [-1, 0, 1]
    max_combo_multiplier = 5

combo_multiplier = 1
combo_multiplier_show_cooldown = 0

beat_speed = max(beat_speed, 10) if 'beat_speed' in locals() else 10  # Ensure valid beat_speed
onsets = [{'time': onset_time,
           'start_y': (((beat_speed - 10) / onset_time) + 20) if onset_time != 0 else float('inf'),
           'y_position': 0,
           'active': True,
           'scored': False,
           'target_index': random.choice(targets_active) if targets_active else None}
          for onset_time in onset_times]


# Game settings
clock = pygame.time.Clock()
fps = 60
beat_start = time.time()  # Start time to sync the onsets

# Load and play the music
pygame.mixer.Sound(audio_path).play()

# Game loop
running = True
while running:
    current_time = time.time() - beat_start
    if end_screen:
        # Display the end screen
        screen.fill(BLACK)
        target1_color = DARK_GREEN
        target2_color = DARK_YELLOW
        target3_color = DARK_BLUE

        # Calculate positions to center text
        score_percentage = math.floor(100 * ((score / maxScore) if score > 0 else 0))
        end_text = end_font.render("Game Over!" if score_percentage < 75 else "you won", True, WHITE)
        end_text_rect = end_text.get_rect(center=(screen.get_width() // 2, 200))

        end_comment_text = score_font.render("you can do better" if score_percentage < 50 else "really good" if score_percentage >= 50 and score_percentage < 75 else "awesome" if score_percentage >= 75 and score_percentage < 100 else "perfection", True, WHITE)
        end_comment_text_rect = end_comment_text.get_rect(center=(screen.get_width() // 2, 250))

        score_text = score_font.render(f"Final Score: {score} ({min(score_percentage, 100)}%)", True, WHITE)
        score_text_rect = score_text.get_rect(center=(screen.get_width() // 2, 300))

        restart_text = score_font.render("Press R to Restart or C to continue", True, WHITE)
        restart_text_rect = restart_text.get_rect(center=(screen.get_width() // 2, 400))

        # Draw the texts with centered positions
        screen.blit(end_text, end_text_rect)
        screen.blit(score_text, score_text_rect)
        screen.blit(restart_text, restart_text_rect)
        screen.blit(end_comment_text, end_comment_text_rect)

    else:
        screen.fill(DARK_GRAY)

    if score_color_cooldown > 0:
        score_color_cooldown -= 1
    else:
        score1_color = WHITE

    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RIGHT:
                scored_hit = False
                for onset in onsets:
                    if onset['active'] and not onset['scored'] and onset['target_index'] == 1:
                        # Check if the beat is within the target zone when Space is pressed
                        if abs(target_y - onset['y_position']) <= tolerance:
                            if combo_multiplier < max_combo_multiplier:
                                combo_multiplier += 1
                            score += 10 * combo_multiplier
                            maxScore += 75
                            combo_multiplier_show_cooldown = 100
                            score_color_cooldown = 75
                            score_color = (0, 255, 0)
                            onset['scored'] = True
                            onset['active'] = False
                            scored_hit = True
                            break
                if not scored_hit and not end_screen:
                    combo_multiplier = 1
                    score -= 10
                    score_color_cooldown = 75
                    score_color = (255, 0, 0)
            elif event.key == pygame.K_LEFT:
                scored_hit = False
                for onset in onsets:
                    if onset['active'] and not onset['scored'] and onset['target_index'] == -1:
                        # Check if the beat is within the target zone when Space is pressed
                        if abs(target_y - onset['y_position']) <= tolerance:
                            if combo_multiplier < max_combo_multiplier:
                                combo_multiplier += 1
                            score += 10 * combo_multiplier
                            maxScore += 75
                            combo_multiplier_show_cooldown = 100
                            score_color_cooldown = 75
                            score_color = (0, 255, 0)
                            onset['scored'] = True
                            onset['active'] = False
                            scored_hit = True
                            break
                if not scored_hit and not end_screen:
                    combo_multiplier = 1
                    score -= 10
                    score_color_cooldown = 75
                    score_color = (255, 0, 0)
            elif event.key == pygame.K_SPACE:
                scored_hit = False
                for onset in onsets:
                    if onset['active'] and not onset['scored'] and onset['target_index'] == 0:
                        # Check if the beat is within the target zone when Space is pressed
                        if abs(target_y - onset['y_position']) <= tolerance:
                            if combo_multiplier < max_combo_multiplier:
                                combo_multiplier += 1
                            score += 10 * combo_multiplier
                            maxScore += 75
                            combo_multiplier_show_cooldown = 100
                            score_color_cooldown = 75
                            score_color = (0, 255, 0)
                            onset['scored'] = True
                            onset['active'] = False
                            scored_hit = True
                            break
                if not scored_hit and not end_screen:
                    combo_multiplier = 1
                    score -= 10
                    score_color_cooldown = 75
                    score_color = (255, 0, 0)
            elif event.key == pygame.K_c and end_screen:  # continue game
                    # Reset necessary variables to restart the game
                    score = 0
                    maxScore = 0
                    end_trigger_time, onset_times, audio_path, song_duration = cycleSong()
                    target0_color = GREEN
                    target1_color = YELLOW
                    target2_color = BLUE
                    beat_speed = max(beat_speed, 10) if 'beat_speed' in locals() else 10  # Ensure valid beat_speed
                    onsets = [{'time': onset_time,
                        'start_y': (((beat_speed - 10) / onset_time) + 20) if onset_time != 0 else float('inf'),
                        'y_position': 0,
                        'active': True,
                        'scored': False,
                        'target_index': random.choice(targets_active) if targets_active else None}
                        for onset_time in onset_times]
                    pygame.mixer.Sound(audio_path).play()
                    beat_start = time.time()
                    current_time = 0
                    end_screen = False  # Exit end screen mode
            elif event.key == pygame.K_r and end_screen:  # restart game
                    # Reset necessary variables to restart the game
                    score = 0
                    maxScore = 0
                    target0_color = GREEN
                    target1_color = YELLOW
                    target2_color = BLUE
                    beat_speed = max(beat_speed, 10) if 'beat_speed' in locals() else 10  # Ensure valid beat_speed
                    onsets = [{'time': onset_time,
                        'start_y': (((beat_speed - 10) / onset_time) + 20) if onset_time != 0 else float('inf'),
                        'y_position': 0,
                        'active': True,
                        'scored': False,
                        'target_index': random.choice(targets_active) if targets_active else None}
                        for onset_time in onset_times]
                    pygame.mixer.Sound(audio_path).stop()
                    pygame.mixer.Sound(audio_path).play()
                    beat_start = time.time()
                    current_time = 0
                    end_screen = False  # Exit end screen mode
    
    if combo_multiplier_show_cooldown > 0:
        combo_multiplier_show_cooldown -= 1
        combo_multiplier_text = combo_multiplier_font.render(f"{combo_multiplier}x", True, LIGHT_GRAY)
        combo_multiplier_rect = combo_multiplier_text.get_rect(center=(screen.get_width() / 2, 50))
        screen.blit(combo_multiplier_text, combo_multiplier_rect)
    
    if end_screen:
        pygame.display.flip()
    # Draw the target zone
    pygame.draw.circle(screen, target0_color if difficulty in ["easy", "hard", "extreme"] else GRAY, (400, target_y), target_radius)
    pygame.draw.circle(screen, target1_color if difficulty in ["normal", "extreme"] else GRAY, (400 - target_radius*2.5, target_y), target_radius)
    pygame.draw.circle(screen, target2_color if difficulty in ["normal", "hard", "extreme"] else GRAY, (400 + target_radius*2.5, target_y), target_radius)
    progress_ratio = current_time / song_duration
    progress_width = int((screen.get_width() - 20) * progress_ratio)
    pygame.draw.rect(screen, GRAY, ((screen.get_width()/2)-progress_width/2, screen.get_height() - 10, progress_width, 10))  # Progress bar at top

    if difficulty in ["normal", "hard", "extreme"]:
        # show a text for the yellow target
        yellow_target_font = targets_font.render(f"LEFT", True, BLACK)
        yellow_target_rect = yellow_target_font.get_rect(center=(400 - target_radius*2.5, target_y))
        screen.blit(yellow_target_font, yellow_target_rect)

    if difficulty in ["easy", "extreme"]:
        # show a text for the green target
        green_target_font = targets_font.render(f"SPACE", True, BLACK)
        green_target_rect = green_target_font.get_rect(center=(400, target_y))
        screen.blit(green_target_font, green_target_rect)

    if difficulty in ["normal", "hard", "extreme"]:
        # show a text for the blue target
        blue_target_font = targets_font.render(f"RIGHT", True, BLACK)
        blue_target_rect = blue_target_font.get_rect(center=(400 + target_radius*2.5, target_y))
        screen.blit(blue_target_font, blue_target_rect)

    # Move onsets downward and draw them
    for onset in onsets:
        if onset['active'] and current_time >= onset['time']:
            onset['y_position'] = onset['start_y'] + beat_speed * (current_time - onset['time'])
            pygame.draw.circle(screen, RED, (400 + target_radius*2.5*onset['target_index'], int(onset['y_position'])), 15)

            if onset['y_position'] >= target_y + tolerance:
                onset['active'] = False
                maxScore += 100
                combo_multiplier = 1

    # Check if all onsets are inactive
    if current_time >= end_trigger_time:
        end_screen = True  # Trigger end screen display
    else:
        # Display score
        score_text = score_font.render(f"Score: {score}/{maxScore}", True, score_color)
        screen.blit(score_text, (10, 10))
        if not end_screen:
            pygame.display.flip()
    clock.tick(fps)
pygame.quit()
