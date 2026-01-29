# Playing XI extractor

import time
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By

from config import WAIT_TIME
from utils import clean_player_name, get_designation, remove_markers, is_valid_player_name


def extract_playing_xi(driver, match_url, match_data):
    squads_url = match_url.replace("live-cricket-scores", "cricket-match-squads")
    driver.get(squads_url)
    time.sleep(WAIT_TIME)
    
    soup = BeautifulSoup(driver.page_source, "html.parser")
    
    team_sections = soup.select("div.cb-col-50.cb-col")
    
    teams_data = []
    for section in team_sections:
        team_info = {"name": "", "players": []}
        
        header = section.select_one("span.cb-font-20, h2, a.cb-lnk-wht, div.cb-font-16")
        if header:
            team_info["name"] = header.get_text(strip=True)
        
        player_links = section.select("a[href*='/profiles/']")
        seen_names = set()
        
        for link in player_links:
            raw_name = link.get_text(strip=True)
            if raw_name and len(raw_name) > 2:
                designation = get_designation(raw_name)
                clean_name = remove_markers(clean_player_name(raw_name))
                
                if is_valid_player_name(clean_name) and clean_name not in seen_names:
                    seen_names.add(clean_name)
                    team_info["players"].append({
                        "name": clean_name,
                        "designation": designation
                    })
        
        team_info["players"] = team_info["players"][:11]
        
        if team_info["players"]:
            teams_data.append(team_info)
    
    if len(teams_data) < 2:
        teams_data = _extract_players_fallback(soup, match_data)
    
    _assign_teams(teams_data, match_data)


def _extract_players_fallback(soup, match_data):
    all_player_links = soup.select("a[href*='/profiles/']")
    all_players = []
    seen_names = set()
    
    for link in all_player_links:
        raw_name = link.get_text(strip=True)
        if raw_name and len(raw_name) > 2:
            designation = get_designation(raw_name)
            clean_name = remove_markers(clean_player_name(raw_name))
            
            if is_valid_player_name(clean_name) and clean_name not in seen_names:
                seen_names.add(clean_name)
                all_players.append({
                    "name": clean_name,
                    "designation": designation
                })
    
    if len(all_players) >= 11:
        return [
            {"name": match_data["match_info"]["team1_name"], "players": all_players[:11]},
            {"name": match_data["match_info"]["team2_name"], "players": all_players[11:22] if len(all_players) >= 22 else []}
        ]
    
    return []


def _assign_teams(teams_data, match_data):
    if len(teams_data) >= 2:
        match_data["playing_11"]["team1"] = teams_data[0]
        match_data["playing_11"]["team1"]["name"] = match_data["match_info"]["team1_name"] or teams_data[0]["name"]
        match_data["playing_11"]["team2"] = teams_data[1]
        match_data["playing_11"]["team2"]["name"] = match_data["match_info"]["team2_name"] or teams_data[1]["name"]
    elif len(teams_data) == 1:
        match_data["playing_11"]["team1"] = teams_data[0]
        match_data["playing_11"]["team1"]["name"] = match_data["match_info"]["team1_name"] or teams_data[0]["name"]
