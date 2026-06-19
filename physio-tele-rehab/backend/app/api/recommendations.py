from fastapi import APIRouter

router = APIRouter()


@router.get("/condition-map")
def condition_map():
    return {
        "Knee Pain": ["Quad Sets", "Straight Leg Raise", "Heel Slides"],
        "Low Back Pain": ["Pelvic Tilts", "Cat Camel", "Bridge"],
        "Shoulder Pain": ["Pendulum", "Scapular Retraction", "Wall Slides"],
        "Stroke Rehab": ["Sit To Stand", "Weight Shifts", "Gait Practice"],
    }


@router.post("/plan")
def plan(data: dict):
    condition = data.get("condition", "General Rehabilitation")
    return {
        "condition": condition,
        "recommendations": [
            "Start With Pain-Free Mobility",
            "Progress Load Gradually",
            "Monitor Pain, Fatigue, And Adherence",
        ],
        "therapist_review_required": True,
    }


@router.post("/adjust")
def adjust(data: dict):
    adherence = float(data.get("current_adherence", 0))
    pain = float(data.get("average_pain", 0))
    if pain >= 6:
        note = "Reduce Intensity And Prioritize Pain-Free Range."
    elif adherence >= 0.8 and pain <= 3:
        note = "Consider Carefully Progressing Intensity."
    else:
        note = "Maintain Current Plan And Reassess."
    return {"adjustment_notes": note, "therapist_review_required": True}
