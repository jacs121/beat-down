import pygame
import time
import librosa
import math
import glob
import win11toast
import os
import random
import requests
import sys
import numpy as np
from librosa.util.exceptions import ParameterError
from librosa.onset import onset_backtrack

# Define current release version
release_version = "v1.1.0"

# GitHub repository details
GITHUB_REPO = "jacs121/beat-down"
LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

def check_for_update():
    try:
        response = requests.get(LATEST_RELEASE_API, timeout=5)
        response.raise_for_status()
        latest_release = response.json()
        
        latest_version = latest_release["tag_name"]
        download_url = latest_release["assets"][0]["browser_download_url"]

        if latest_version != release_version:
            win11toast.toast(
                "Update Available",
                f"A new version ({latest_version}) is available. Click to download.",
                on_click=lambda: download_update(download_url, latest_version)
            )
    except Exception as e:
        print(f"Failed to check for updates: {e}")

def download_update(url, latest_version):
    """Download the latest version and close the game after completion."""
    exe_path = os.path.join(os.getcwd(), f"beat down - {latest_version}.exe")  # Save as "beat down - {version}.exe"
    try:
        response = requests.get(url, stream=True)
        with open(exe_path, "wb") as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        
        win11toast.toast("Download Complete", "The latest version has been downloaded. you can now use the new file.")

        # Close the game after downloading
        sys.exit(0)
    except Exception as e:
        print(f"Download failed: {e}")

# Run update check if script is in executable mode
if getattr(sys, 'frozen', False):  # Checks if running as an exe
    check_for_update()


songI = -1
def get_adaptive_parameters(tempo, onset_env, sr):
    # normalize the envelope to [0,1]
    if onset_env.max() > 0:
        onset_env = onset_env / np.max(onset_env)

    # dynamic range
    dynamic_range = np.max(onset_env) - np.min(onset_env)

    # a more modest delta
    #    – 75th percentile of the *normalized* envelope is in [0,1]
    #    – scale it by a constant in [0.5, 0.8] instead of multiplying back by the big dynamic_range
    perc75 = np.percentile(onset_env, 75)
    delta  = perc75 * (0.65 + 0.25 * (1 - dynamic_range))

    # beat-based windows (unchanged)
    beat_interval   = 60.0 / tempo
    frames_per_beat = int(beat_interval * sr / 512)
    
    print(delta)

    return {
        'delta':    delta,
        'pre_max':  int(frames_per_beat * 1.5),
        'post_max': int(frames_per_beat * 1.5),
        'pre_avg':  max(3, int(frames_per_beat * 0.7)),
        'post_avg': max(3, int(frames_per_beat * 0.7)),
        'wait':     max(1, int(frames_per_beat * 0.3)),
    }

def cycleSong(delta=0.22, pre_max=10.5, post_max=10.5, auto:bool = True):
    global songI
    song_files = sorted(glob.glob("songs/*.MP3"))
    
    if not song_files:
        win11toast.toast("Beat Rhythm - no songs available", "Please add songs to the songs folder.")
        sys.exit()
    
    songI = (songI + 1) % len(song_files)
    audio_path = song_files[songI]
    
    pygame.display.set_caption(f"Beat down - waiting...")
    print(f"Loading {audio_path}...")
    
    # Load audio and extract features
    y, sr = librosa.load(audio_path, sr=None)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    tempo, _ = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
    
    # Parameter selection
    if auto:
        params = get_adaptive_parameters(tempo, onset_env, sr)
    else:
        params = {
            'delta': delta,
            'pre_max': int(pre_max),
            'post_max': int(post_max),
            'pre_avg': 5,
            'post_avg': 5,
            'wait': 2
        }

    # Detect onsets with selected parameters
    raw_frames = librosa.onset.onset_detect(
        y=y,
        sr=sr,
        delta=params['delta'],
        pre_max=params['pre_max'],
        post_max=params['post_max'],
        pre_avg=params['pre_avg'],
        post_avg=params['post_avg'],
        wait=params['wait'],
        backtrack=False,
        onset_envelope=onset_env
    )
    
    if raw_frames.size > 0:
        try:
            onset_frames = onset_backtrack(raw_frames, onset_env)
        except ParameterError:
            onset_frames = raw_frames
    else:
        onset_frames = raw_frames
        
    # Convert results
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)
    song_duration = librosa.get_duration(y=y, sr=sr)
    end_trigger_time = song_duration - 10  # 10 seconds before end
    
    pygame.display.set_caption(f"Beat down - {os.path.basename(audio_path)}")
    
    return end_trigger_time, onset_times, audio_path, song_duration

if not os.path.exists("songs"):
    os.mkdir("songs")

if len(glob.glob("songs/*.MP3")) == 0:
    win11toast.toast("Beat Rhythm - no songs available", "please add songs by adding them to songs folder")
    sys.exit()

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
# Target zone settings
target_y = 550
target_radius = 30
target0_color = GREEN
target1_color = YELLOW
target2_color = BLUE
next_song_color = WHITE
score = 0
maxScore = 0

score_font = pygame.font.Font(None, 36)
end_font = pygame.font.Font(None, 48)  # Font for end screen text
combo_multiplier_font = pygame.font.Font(None, 45)
targets_font = pygame.font.Font(None, 25)
info_font = pygame.font.Font(None, 20)

pygame.display.set_caption("Beat down")

score_color = WHITE
score_color_cooldown = 0
menu_screen = True  # Variable to track if end screen should be displayed

targets_active = []
songList = sorted(glob.glob("songs/*.MP3"))
difficulty = "normal"
tolerance = 40
beat_speed = 155  # Speed at which onsets move down the screen (pixels per second)
targets_active = [-1, 1]
max_combo_multiplier = 10

DIFFICULTY_SETTINGS = {
    "easy": {"tolerance": 45, "beat_speed": 100, "targets": [0], "max_combo": 15},
    "normal": {"tolerance": 35, "beat_speed": 155, "targets": [-1, 1], "max_combo": 10},
    "hard": {"tolerance": 35, "beat_speed": 200, "targets": [-1, 0, 1], "max_combo": 7},
    "extreme": {"tolerance": 30, "beat_speed": 230, "targets": [-1, 0, 1], "max_combo": 5},
}

def change_difficulty(level="normal"):
    global tolerance, beat_speed, targets_active, max_combo_multiplier, difficulty
    difficulty = level
    settings = DIFFICULTY_SETTINGS[level]
    tolerance = settings["tolerance"]
    beat_speed = settings["beat_speed"]
    targets_active = settings["targets"]
    max_combo_multiplier = settings["max_combo"]

DIFFICULTIES = ["easy", "normal", "hard", "extreme"]
def cycle_difficulty(direction=1):
    global difficulty
    idx = DIFFICULTIES.index(difficulty) + direction
    difficulty = DIFFICULTIES[max(0, min(idx, len(DIFFICULTIES) - 1))]
    change_difficulty(difficulty)

combo_multiplier = 1
combo_multiplier_show_cooldown = 0


# Game settings
clock = pygame.time.Clock()
fps = 60
beat_start = time.time()  # Start time to sync the onsets
onsets = []
audio_path = songList[0]
force_next_song = False

# Game loop
start_menu = True
running = True
while running:
    current_time = time.time() - beat_start
    if menu_screen:
        # Display the end screen
        screen.fill(BLACK)

        # Calculate positions to center text
        score_percentage = math.floor(100 * ((score / maxScore) if score > 0 else 0))
        
        difficulty_text = combo_multiplier_font.render(difficulty.upper(), True, WHITE)
        difficulty_rect = difficulty_text.get_rect(center=(screen.get_width() / 2, 50))
        
        info1_text = info_font.render(f"target hit tolerance: {tolerance}", True, WHITE)
        info1_rect = info1_text.get_rect(left=screen.get_rect().left)
        info1_rect.bottom = 20
        
        info2_text = info_font.render(f"circles speed: {beat_speed}", True, WHITE)
        info2_rect = info2_text.get_rect(left=screen.get_rect().left)
        info2_rect.bottom = 40
        
        info3_text = info_font.render(f"max combos: {max_combo_multiplier}", True, WHITE)
        info3_rect = info3_text.get_rect(left=screen.get_rect().left)
        info3_rect.bottom = 60
        
        next_song_text = info_font.render(f"next up: {".".join(os.path.basename(songList[(songI+1) % len(songList)]).split(".")[:-1])}", True, next_song_color)
        next_song_rect = next_song_text.get_rect(left=screen.get_rect().left)
        next_song_rect.bottom = screen.get_rect().bottom
        

        if start_menu:
            end_text = end_font.render("beat down", True, WHITE)
        else:
            end_text = end_font.render("Game Over!" if score_percentage < 75 else "you won", True, WHITE)
        end_text_rect = end_text.get_rect(center=(screen.get_width() // 2, 200))
        if not start_menu:
            end_comment_text = score_font.render("you can do better" if score_percentage < 50 else "really good" if score_percentage >= 50 and score_percentage < 75 else "awesome" if score_percentage >= 75 and score_percentage < 100 else "perfection", True, WHITE)
            end_comment_text_rect = end_comment_text.get_rect(center=(screen.get_width() // 2, 250))

            score_text = score_font.render(f"Final Score: {score} ({score_percentage}%)", True, WHITE)
            score_text_rect = score_text.get_rect(center=(screen.get_width() // 2, 300))

            restart_text = score_font.render("Press R to Restart or C to continue", True, WHITE)
            
            # Draw the texts with centered positions
            screen.blit(score_text, score_text_rect)
            screen.blit(end_comment_text, end_comment_text_rect)
        else:
            restart_text = score_font.render("press Enter to start", True, WHITE)
        restart_text_rect = restart_text.get_rect(center=(screen.get_width() // 2, 400))

        # Draw the rest of the texts with centered positions
        screen.blit(end_text, end_text_rect)
        screen.blit(restart_text, restart_text_rect)
        screen.blit(restart_text, restart_text_rect)
        screen.blit(difficulty_text, difficulty_rect)
        screen.blit(info1_text, info1_rect)
        screen.blit(info2_text, info2_rect)
        screen.blit(info3_text, info3_rect)
        screen.blit(next_song_text, next_song_rect)

    else:
        screen.fill(DARK_GRAY)

    if score_color_cooldown > 0:
        score_color_cooldown -= 1
    else:
        score_color = WHITE

    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RIGHT and not menu_screen:
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
                if not scored_hit and not menu_screen:
                    combo_multiplier = 1
                    score -= 10
                    score_color_cooldown = 75
                    score_color = (255, 0, 0)
            elif event.key == pygame.K_LEFT and not menu_screen:
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
                if not scored_hit and not menu_screen:
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
                if not scored_hit and not menu_screen:
                    combo_multiplier = 1
                    score -= 10
                    score_color_cooldown = 75
                    score_color = (255, 0, 0)
            elif ((event.key == pygame.K_c and not start_menu) or (event.key == pygame.K_RETURN and start_menu)) and menu_screen:  # continue game
                next_song_color = WHITE
                # Reset necessary variables to restart the game
                score = 0
                maxScore = 0
                end_trigger_time, onset_times, audio_path, song_duration = cycleSong()
                target0_color = GREEN
                target1_color = YELLOW
                target2_color = BLUE
                beat_speed = max(beat_speed, 10) if 'beat_speed' in locals() else 10  # Ensure valid beat_speed
                onsets = [{'time': onset_time,
                    'start_y': target_y - (beat_speed * 1.5) + 20,  # Start higher above the target
                    'y_position': target_y - (beat_speed * 1.5) + 20,  # Ensures proper movement
                    'active': True,
                    'scored': False,
                    'target_index': random.choice(targets_active) if targets_active else None}
                    for onset_time in onset_times]
                pygame.mixer.music.stop()
                pygame.mixer.music.load(audio_path)
                pygame.mixer.music.play()
                beat_start = time.time() + 0.1  # Small offset to compensate for delay
                current_time = 0
                menu_screen = False  # Exit end screen mode
                start_menu = False
            elif event.key == pygame.K_r and menu_screen and not start_menu:  # restart game
                next_song_color = WHITE
                # Reset necessary variables to restart the game
                score = 0
                maxScore = 0
                target0_color = GREEN
                target1_color = YELLOW
                target2_color = BLUE
                beat_speed = max(beat_speed, 10) if 'beat_speed' in locals() else 10  # Ensure valid beat_speed
                onsets = [{'time': onset_time,
                    'start_y': target_y - (beat_speed * 1.5),  # Start higher above the target
                    'y_position': target_y - (beat_speed * 1.5),  # Ensures proper movement
                    'active': True,
                    'scored': False,
                    'target_index': random.choice(targets_active) if targets_active else None}
                    for onset_time in onset_times]
                pygame.mixer.music.stop()
                pygame.mixer.music.load(audio_path)
                pygame.mixer.music.play()
                beat_start = time.time() + 0.1  # Small offset to compensate for delay
                current_time = 0
                menu_screen = False  # Exit end screen mode
            elif event.key == pygame.K_UP and menu_screen:
                cycle_difficulty(1)
            elif event.key == pygame.K_DOWN and menu_screen:
                cycle_difficulty(-1)
            elif event.key == pygame.K_LEFT and menu_screen:
                songI = (songI - 1) % len(songList)
                force_next_song = True
                next_song_color = YELLOW

            elif event.key == pygame.K_RIGHT and menu_screen:
                songI = (songI + 1) % len(songList)
                force_next_song = True
                next_song_color = YELLOW
            elif event.key == pygame.K_ESCAPE and not menu_screen:
                menu_screen = True
                pygame.mixer.music.stop()
                score = 0
                maxScore = 0

    if combo_multiplier_show_cooldown > 0 and not menu_screen:
        combo_multiplier_show_cooldown -= 1
        combo_multiplier_text = combo_multiplier_font.render(f"{combo_multiplier}x", True, LIGHT_GRAY)
        combo_multiplier_rect = combo_multiplier_text.get_rect(center=(screen.get_width() / 2, 50))
        screen.blit(combo_multiplier_text, combo_multiplier_rect)

    # Draw the target zone
    pygame.draw.circle(screen, target0_color if -1 in targets_active else GRAY, (400 - target_radius*2.5, target_y), target_radius)
    pygame.draw.circle(screen, target1_color if 0 in targets_active else GRAY, (400, target_y), target_radius)
    pygame.draw.circle(screen, target2_color if 1 in targets_active else GRAY, (400 + target_radius*2.5, target_y), target_radius)
    if not menu_screen:
        progress_ratio = current_time / (song_duration if song_duration > 0 else 1)
        progress_width = int((screen.get_width() - 20) * progress_ratio)
        pygame.draw.rect(screen, GRAY, ((screen.get_width()/2)-progress_width/2, screen.get_height() - 10, progress_width, 10))  # Progress bar at top

    if -1 in targets_active:
        # show a text for the yellow target
        yellow_target_font = targets_font.render(f"LEFT", True, BLACK)
        yellow_target_rect = yellow_target_font.get_rect(center=(400 - target_radius*2.5, target_y))
        screen.blit(yellow_target_font, yellow_target_rect)

    if 0 in targets_active:
        # show a text for the green target
        green_target_font = targets_font.render(f"SPACE", True, BLACK)
        green_target_rect = green_target_font.get_rect(center=(400, target_y))
        screen.blit(green_target_font, green_target_rect)

    if 1 in targets_active:
        # show a text for the blue target
        blue_target_font = targets_font.render(f"RIGHT", True, BLACK)
        blue_target_rect = blue_target_font.get_rect(center=(400 + target_radius*2.5, target_y))
        screen.blit(blue_target_font, blue_target_rect)

    if not menu_screen:
        # Move onsets downward and draw them
        for onset in onsets:
            if onset['active']:
                time_since_onset = current_time - onset['time']
                onset['y_position'] = onset['start_y'] + beat_speed * time_since_onset
                pygame.draw.circle(screen, RED, (400 + target_radius*2.5*onset['target_index'], int(onset['y_position'])), 15)
                

                if onset['y_position'] >= target_y + tolerance:
                    onset['active'] = False
                    maxScore += 100
                    combo_multiplier = 1

        # Check if all onsets are inactive
        if current_time >= end_trigger_time:
            menu_screen = True  # Trigger end screen display
        else:
            # Display score
            score_text = score_font.render(f"Score: {score}/{maxScore}", True, score_color)
            screen.blit(score_text, (10, 10))
            if not menu_screen:
                pygame.display.flip()
    else:
        pygame.display.flip()
    clock.tick(fps)
pygame.quit()
