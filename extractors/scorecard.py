# Scorecard extractor

import re
import time
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By

from config import WAIT_TIME
from utils import remove_markers, is_valid_player_name, parse_dismissal, is_numeric


def extract_scorecard(driver, match_url, match_data):
    scorecard_url = match_url.replace("live-cricket-scores", "live-cricket-scorecard")
    driver.get(scorecard_url)
    time.sleep(WAIT_TIME)
    
    soup = BeautifulSoup(driver.page_source, "html.parser")
    page_text = driver.find_element(By.TAG_NAME, "body").text
    lines = [l.strip() for l in page_text.split('\n') if l.strip()]
    
    innings_headers = _find_innings_headers(lines)
    _fill_missing_scores(innings_headers, match_data)
    
    batter_indices = [i for i, line in enumerate(lines) if line == "Batter"]
    bowler_indices = [i for i, line in enumerate(lines) if line == "Bowler"]
    
    for innings_num, batter_idx in enumerate(batter_indices):
        innings_info = _parse_innings(
            lines, innings_num, batter_idx, 
            innings_headers, bowler_indices
        )
        
        if innings_info["batting"]:
            match_data["scorecard"].append(innings_info)


def _find_innings_headers(lines):
    innings_headers = []
    for i, line in enumerate(lines):
        if "innings" in line.lower() and re.search(r'\d+[/-]\d+', line):
            innings_headers.append((i, line))
    return innings_headers


def _fill_missing_scores(innings_headers, match_data):
    for idx, header in innings_headers:
        score_match = re.search(r'(\d+)[/-](\d+)\s*\(([\d.]+)', header)
        if score_match:
            score = f"{score_match.group(1)}/{score_match.group(2)} ({score_match.group(3)} Ov)"
            
            if not match_data["match_info"]["team1_score"]:
                match_data["match_info"]["team1_score"] = score
            elif not match_data["match_info"]["team2_score"]:
                match_data["match_info"]["team2_score"] = score


def _parse_innings(lines, innings_num, batter_idx, innings_headers, bowler_indices):
    innings_info = {
        "innings": f"Innings {innings_num + 1}",
        "batting_team": "",
        "total_score": "",
        "total_overs": "",
        "batting": [],
        "bowling": []
    }
    
    for hi, header in innings_headers:
        if hi < batter_idx and hi > batter_idx - 25:
            innings_info["batting_team"] = header.split("Innings")[0].strip()
            score_match = re.search(r'(\d+)[/-](\d+)\s*\(([\d.]+)', header)
            if score_match:
                innings_info["total_score"] = f"{score_match.group(1)}/{score_match.group(2)}"
                innings_info["total_overs"] = score_match.group(3)
            break
    
    innings_info["batting"] = _parse_batting(lines, batter_idx)
    
    bowling_idx = _find_bowling_index(batter_idx, bowler_indices)
    if bowling_idx:
        innings_info["bowling"] = _parse_bowling(lines, bowling_idx)
    
    return innings_info


def _parse_batting(lines, batter_idx):
    batting = []
    i = batter_idx + 1
    
    while i < len(lines) and lines[i] in ["R", "B", "4s", "6s", "SR", ""]:
        i += 1
    
    while i < len(lines):
        line = lines[i]
        
        if line in ["Extras", "Total", "Did not Bat", "Fall of Wickets", "Bowler", "Yet to Bat"]:
            break
        
        if is_valid_player_name(remove_markers(line)):
            entry = _parse_batting_entry(lines, i)
            if entry:
                batting.append(entry["data"])
                i = entry["next_index"]
                continue
        
        i += 1
    
    return batting


def _parse_batting_entry(lines, start_idx):
    player_name = remove_markers(lines[start_idx])
    dismissal = ""
    runs = balls = fours = sixes = sr = "0"
    
    j = start_idx + 1
    
    if j < len(lines):
        next_line = lines[j]
        if parse_dismissal(next_line) or next_line.lower() == "not out":
            dismissal = next_line
            j += 1
    
    stats = []
    while j < len(lines) and len(stats) < 5:
        if is_numeric(lines[j]):
            stats.append(lines[j])
            j += 1
        elif is_valid_player_name(remove_markers(lines[j])) or lines[j] in ["Extras", "Total", "Bowler"]:
            break
        else:
            j += 1
    
    if len(stats) >= 5:
        runs, balls, fours, sixes, sr = stats[:5]
    
    return {
        "data": {
            "batsman": player_name,
            "dismissal": dismissal if dismissal else "not out",
            "runs": runs,
            "balls": balls,
            "fours": fours,
            "sixes": sixes,
            "strike_rate": sr
        },
        "next_index": j
    }


def _find_bowling_index(batter_idx, bowler_indices):
    for bi in bowler_indices:
        if bi > batter_idx:
            return bi
    return None


def _parse_bowling(lines, bowling_idx):
    bowling = []
    i = bowling_idx + 1
    
    while i < len(lines) and lines[i] in ["O", "M", "R", "W", "NB", "WD", "ECO", ""]:
        i += 1
    
    while i < len(lines):
        line = lines[i]
        
        if line in ["Extras", "Total", "Batter", "Fall of Wickets", "Yet to Bat"]:
            break
        
        if is_valid_player_name(line):
            entry = _parse_bowling_entry(lines, i)
            if entry:
                bowling.append(entry["data"])
                i = entry["next_index"]
                continue
        
        i += 1
    
    return bowling


def _parse_bowling_entry(lines, start_idx):
    bowler_name = lines[start_idx]
    j = start_idx + 1
    stats = []
    
    while j < len(lines) and len(stats) < 8:
        if is_numeric(lines[j]) or re.match(r'^\d+\.?\d*$', lines[j]):
            stats.append(lines[j])
            j += 1
        elif is_valid_player_name(lines[j]) or lines[j] in ["Extras", "Total", "Batter"]:
            break
        else:
            j += 1
    
    if len(stats) >= 5:
        return {
            "data": {
                "bowler": bowler_name,
                "overs": stats[0],
                "maidens": stats[1],
                "runs": stats[2],
                "wickets": stats[3],
                "economy": stats[-1] if len(stats) > 4 else "0"
            },
            "next_index": j
        }
    
    return None
