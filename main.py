from fastapi import FastAPI, status, Query, Request
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import httpx
import asyncio
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")

app = FastAPI() # samo generuje dokumentacje swagger ui http://127.0.0.1:8000/docs
app.mount("/static", StaticFiles(directory="static"), name="static")
headers = {"Content-Type": "application/json","x-rapidapi-key": "fe42bcb142mshccd913463aa0edep115d55jsne63458aafa83", "x-rapidapi-host": "sportapi7.p.rapidapi.com"}

@app.get("/", response_class=FileResponse)
async def read_root():
    return "static/index.html"

@app.get("/analizuj")
async def analyze(request : Request, team_id: str = "32", num: int = 5):
    try:
        id = int(team_id)
    except ValueError:
        return HTMLResponse(content="<h1>ID drużyny musi być liczbą</h1>", status_code=400)
    url = f"https://sportapi7.p.rapidapi.com/api/v1/team/{team_id}/events/last/0"
    url_details = f"https://sportapi7.p.rapidapi.com/api/v1/team/{team_id}"
    async with httpx.AsyncClient() as client:
        response_event, response_details = await asyncio.gather(client.get(url, headers=headers), client.get(url_details, headers=headers))
        if response_event.status_code != 200:
            print(response_event.status_code)
            return HTMLResponse(content="<h1>Błąd API</h1>", status_code=502)
            
        data = response_event.json()
        details = response_details.json()

    results = data.get("events", [])[-num:][::-1]
    if not results:
        return HTMLResponse(content="<h1>Nie znaleziono danych dla podanego ID drużyny.</h1>", status_code=status.HTTP_404_NOT_FOUND)
    stats = {
        "team_name" : details.get("team", {}).get("name", "Nieznana drużyna"), # nazwa druzyny
        "home_team" : [], # lista druzyn domowych, home_team[i] oznacza druzyne grajaca u siebie w i-tym meczu
        "away_team" : [], # lista druzyn na wyjezdzie, jak wyzej
        "home_goals": [], # lista goli druzyny domowej dla i-tego meczu
        "away_goals" : [], # to co wyzej dla wyjazdowej
        "tournaments" : [], # lista z turniejami
        "goals_scored" : 0, # suma strzelonych bramek
        "goals_received" : 0, # suma straconych
        "points" : 0, # suma punktow
        "points_avg" : 0
    }
    
    for event in results:
        h_score = event.get("homeScore", {}).get("current", 0)
        a_score = event.get("awayScore", {}).get("current", 0)
        winner = event.get("winnerCode", 0)

        stats["tournaments"].append(event["tournament"]["name"])
        stats["away_team"].append(event["awayTeam"]["name"])
        stats["home_team"].append(event["homeTeam"]["name"])
        stats["home_goals"].append(h_score)
        stats["away_goals"].append(a_score)

        if event["homeTeam"]["id"] == id:
            stats["goals_scored"] += h_score
            stats["goals_received"] += a_score
            if winner == 1:
                stats["points"] += 3
            elif winner == 3:
                stats["points"] += 1
        
        else:
            stats["goals_scored"] += a_score
            stats["goals_received"] += h_score
            if winner == 2:
                stats["points"] += 3
            elif winner == 3:
                stats["points"] += 1
    matches_no = len(results)
    if matches_no > 0:
        stats["points_avg"] = round(stats["points"] / matches_no, 2)
        stats["goals_avg"] = round(stats["goals_scored"] / matches_no, 2)
    else:
        stats["points_avg"] = 0
        stats["goals_avg"] = 0

    return templates.TemplateResponse("forma.html", {
        "request" : request,
        "t" : stats
    })

@app.get("/h2h")
async def h2h(request : Request, team1_id : str, team2_id : str, num : int = 5):
    try:
        id1, id2 = int(team1_id), int(team2_id)
    except ValueError:
        return HTMLResponse(content="<h1>ID drużyny musi być liczbą</h1>", status_code=400)
    url1 = f"https://sportapi7.p.rapidapi.com/api/v1/team/{team1_id}/events/last/0"
    url1_details = f"https://sportapi7.p.rapidapi.com/api/v1/team/{team1_id}"

    url2 = f"https://sportapi7.p.rapidapi.com/api/v1/team/{team2_id}/events/last/0"
    url2_details = f"https://sportapi7.p.rapidapi.com/api/v1/team/{team2_id}"

    async with httpx.AsyncClient() as client:
        response1_event, response1_details = await asyncio.gather(client.get(url1, headers=headers), client.get(url1_details, headers=headers))
        response2_event, response2_details = await asyncio.gather(client.get(url2, headers=headers), client.get(url2_details, headers=headers))
        if response1_event.status_code != 200 or response2_event.status_code != 200:
            return HTMLResponse(content="<h1>Błąd API</h1>", status_code=502)
            
        data1 = response1_event.json()
        details1 = response1_details.json()

        data2 = response2_event.json()
        details2 = response2_details.json()

    results1 = data1.get("events", [])[-num:][::-1]
    results2 = data2.get("events", [])[-num:][::-1]

    if not results1 or not results2:
        return HTMLResponse(content="<h1>Nie znaleziono danych dla podanego ID drużyny.</h1>", status_code=status.HTTP_404_NOT_FOUND)
    
    stats1 = {
        "team_name" : details1.get("team", {}).get("name", "Nieznana drużyna"), # nazwa druzyny
        "goals_scored" : 0, # suma strzelonych bramek
        "goals_received" : 0, # suma straconych
        "points" : 0, # suma punktow
        "goals_scored_period1" : 0,
        "goals_scored_period2" : 0
    }

    stats2 = {
        "team_name" : details2.get("team", {}).get("name", "Nieznana drużyna"), # nazwa druzyny
        "goals_scored" : 0, # suma strzelonych bramek
        "goals_received" : 0, # suma straconych
        "points" : 0, # suma punktow
        "goals_scored_period1" : 0,
        "goals_scored_period2" : 0
    }
    
    for event in results1:
        h_score = event.get("homeScore", {}).get("current", 0)
        a_score = event.get("awayScore", {}).get("current", 0)
        winner = event.get("winnerCode", 0)

        if event["homeTeam"]["id"] == id1:
            stats1["goals_scored"] += h_score
            stats1["goals_received"] += a_score
            stats1["goals_scored_period1"] += event.get("homeScore", {}).get("period1", 0)
            stats1["goals_scored_period2"] += event.get("homeScore", {}).get("period2", 0)
            if winner == 1:
                stats1["points"] += 3
            elif winner == 3:
                stats1["points"] += 1
        
        else:
            stats1["goals_scored"] += a_score
            stats1["goals_received"] += h_score
            stats1["goals_scored_period1"] += event.get("awayScore", {}).get("period1", 0)
            stats1["goals_scored_period2"] += event.get("awayScore", {}).get("period2", 0)
            if winner == 2:
                stats1["points"] += 3
            elif winner == 3:
                stats1["points"] += 1

    for event in results2:
        h_score = event.get("homeScore", {}).get("current", 0)
        a_score = event.get("awayScore", {}).get("current", 0)
        winner = event.get("winnerCode", 0)

        if event["homeTeam"]["id"] == id2:
            stats2["goals_scored"] += h_score
            stats2["goals_received"] += a_score
            stats2["goals_scored_period1"] += event.get("homeScore", {}).get("period1", 0)
            stats2["goals_scored_period2"] += event.get("homeScore", {}).get("period2", 0)
            if winner == 1:
                stats2["points"] += 3
            elif winner == 3:
                stats2["points"] += 1
        
        else:
            stats2["goals_scored"] += a_score
            stats2["goals_received"] += h_score
            stats2["goals_scored_period1"] += event.get("awayScore", {}).get("period1", 0)
            stats2["goals_scored_period2"] += event.get("awayScore", {}).get("period2", 0)
            if winner == 2:
                stats2["points"] += 3
            elif winner == 3:
                stats2["points"] += 1

    return templates.TemplateResponse("h2h.html", {
        "request": request, 
        "t1": stats1, 
        "t2": stats2
    })


    
    