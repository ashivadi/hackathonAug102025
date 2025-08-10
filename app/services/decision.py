def score_decision(relationship_value=1.0, wellbeing_delta=0.0, goal_disruption=0.5, schedule_cost=0.5):
    s = 0.4*relationship_value + 0.3*wellbeing_delta - 0.2*goal_disruption - 0.1*schedule_cost
    return max(-1.0, min(1.0, s))
