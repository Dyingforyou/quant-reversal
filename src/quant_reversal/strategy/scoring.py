from ..models import Candidate
def grade(score:float,a:float=80,b:float=70,watch:float=60)->str:return "A" if score>=a else "B" if score>=b else "WATCH" if score>=watch else "REJECT"
def finalize(candidate:Candidate,weights,a:float=80,b:float=70,watch:float=60)->Candidate:
    normalized={
        "sector":candidate.sector_score/20,"stock":candidate.stock_score/20,
        "break":candidate.break_score/15,"ma5":candidate.ma5_score/15,
        "auction":candidate.auction_score/20,"height_rank":candidate.height_score,
        "turnover":candidate.turnover_score,"sentiment":candidate.sentiment_score,
    }
    candidate.total_score=round(sum(normalized[name]*getattr(weights,f"{name}_weight") for name in normalized),2)
    candidate.grade=grade(candidate.total_score,a,b,watch); return candidate
