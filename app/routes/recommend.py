from fastapi import APIRouter, HTTPException, Query

from app.services.rec_engine import rec_engine

router = APIRouter()


@router.get("/recommendations", summary="Get personalized product recommendations")
async def get_recommendations(
    query: str = Query(..., description="User's search query"),
    user_id: str | None = None,
    top_k: int = Query(3, ge=1, le=20),
):
    try:
        recommendations = await rec_engine.get_recommendations(query, user_id=user_id, top_k=top_k)
        return {"recommendations": recommendations, "count": len(recommendations)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation error: {e}")
