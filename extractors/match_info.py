# Match info extractor

import re
import time
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By

from config import WAIT_TIME, TEAM_ABBREVIATIONS
from utils import (
    is_valid_player_name, match_team_abbreviation, extract_score_from_text
)


def create_empty_match_data(match_url):
    return {
        "match_url": match_url,
        "match_title": "",
        "match_info": {
            "team1_name": "",
            "team1_score": "",
            "team2_name": "",
            "team2_score": "",
            "venue": "",
            "date": "",
            "toss": "",
            "result": "",
            "winner": "",
            "player_of_match": "",
            "umpires": "",
            "match_referee": ""
        },
        "playing_11": {
            "team1": {"name": "", "players": []},
            "team2": {"name": "", "players": []}
        },
        "scorecard": []
    }


def extract_title_and_teams(driver, match_data):
    try:
        h1 = driver.find_element(By.TAG_NAME, "h1")
        match_data["match_title"] = (
            h1.text
            .replace(" - Live Cricket Score", "")
            .replace(" - Commentary", "")
            .strip()
        )
    except:
        pass
    
    title = match_data["match_title"]
    if " vs " in title.lower():
        teams_part = title.split(",")[0]
        teams = teams_part.lower().replace(" vs ", " vs ").split(" vs ")
        if len(teams) >= 2:
            match_data["match_info"]["team1_name"] = teams[0].strip().title()
            match_data["match_info"]["team2_name"] = teams[1].strip().title()


def extract_scores(lines, match_data):
    team1_name = match_data["match_info"]["team1_name"]
    team2_name = match_data["match_info"]["team2_name"]
    
    for i, line in enumerate(lines):
        if re.match(r'^[A-Z][A-Z0-9a-z\s]{0,14}$', line) and i + 1 < len(lines):
            next_line = lines[i + 1]
            team_abbr = line.strip()
            
            score = extract_score_from_text(next_line)
            
            if score:
                team_match = match_team_abbreviation(
                    team_abbr, team1_name, team2_name, TEAM_ABBREVIATIONS
                )
                
                if team_match == 'team1' and not match_data["match_info"]["team1_score"]:
                    match_data["match_info"]["team1_score"] = score
                elif team_match == 'team2' and not match_data["match_info"]["team2_score"]:
                    match_data["match_info"]["team2_score"] = score
                elif not match_data["match_info"]["team1_score"]:
                    match_data["match_info"]["team1_score"] = score
                elif not match_data["match_info"]["team2_score"]:
                    match_data["match_info"]["team2_score"] = score


def extract_result(lines, match_data):
    for line in lines:
        line_lower = line.lower()
        if (" won by " in line_lower or " tied" in line_lower or "match drawn" in line_lower) and len(line) < 100:
            if not match_data["match_info"]["result"]:
                match_data["match_info"]["result"] = line.strip()
                if " won by " in line_lower:
                    match_data["match_info"]["winner"] = line.split(" won by ")[0].strip()
            break


def extract_player_of_match(lines, match_data):
    for i, line in enumerate(lines):
        if "player of the match" in line.lower():
            for j in range(i + 1, min(i + 4, len(lines))):
                candidate = lines[j].strip()
                
                if re.match(r'^[a-z]+-[a-z]+', candidate):
                    continue
                
                if any(x in candidate.lower() for x in ["local", "gmt", "ist", "time", "http", "view", "click", ":"]):
                    continue
                
                if (candidate and 
                    3 < len(candidate) < 40 and 
                    is_valid_player_name(candidate) and
                    any(c.isupper() for c in candidate)):
                    match_data["match_info"]["player_of_match"] = candidate
                    return
            break


def extract_match_facts(driver, match_url, match_data):
    info_url = match_url.replace("live-cricket-scores", "cricket-match-facts")
    driver.get(info_url)
    time.sleep(2)
    
    page_text = driver.find_element(By.TAG_NAME, "body").text
    lines = [l.strip() for l in page_text.split('\n') if l.strip()]
    
    for i, line in enumerate(lines):
        line_lower = line.lower()
        
        if line_lower == "venue" and i + 1 < len(lines):
            match_data["match_info"]["venue"] = lines[i + 1]
        
        if line_lower == "date" and i + 1 < len(lines):
            match_data["match_info"]["date"] = lines[i + 1]
        
        if line_lower == "toss" and i + 1 < len(lines):
            match_data["match_info"]["toss"] = lines[i + 1]
        
        if line_lower == "umpires" and i + 1 < len(lines):
            match_data["match_info"]["umpires"] = lines[i + 1]
        
        if line_lower == "match referee" and i + 1 < len(lines):
            match_data["match_info"]["match_referee"] = lines[i + 1]
