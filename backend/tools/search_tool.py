from database import run_query

def search_similar_incidents(query_text):
    stop_words = {'the','a','an','is','are','was','and','or','for','in','on','at','to'}
    words = [w for w in query_text.lower().split()
             if w not in stop_words and len(w) > 3]

    if not words:
        return "No similar past incidents found."

    like_conditions = " OR ".join([
        f"LOWER(title) LIKE '%{w}%' OR LOWER(human_root_cause) LIKE '%{w}%' OR LOWER(agent_root_cause) LIKE '%{w}%'"
        for w in words[:5]
    ])

    sql = f"""
        SELECT title,
               agent_root_cause,
               agent_resolution,
               human_root_cause,
               human_resolution,
               agent_was_correct,
               resolution_confidence
        FROM past_incidents
        WHERE {like_conditions}
        ORDER BY
          CASE resolution_confidence
            WHEN 'human_verified'  THEN 1
            WHEN 'human_corrected' THEN 2
            ELSE 3
          END
        LIMIT 3
    """
    rows = run_query(sql, fetch=True)

    if not rows:
        return "No similar past incidents found in history."

    output = "SIMILAR PAST INCIDENTS:\n\n"
    for row in rows:
        # Use human resolution if available, fall back to agent
        best_root   = row[3] if row[3] else row[1]
        best_fix    = row[4] if row[4] else row[2]
        verified    = "Human verified" if row[5] else "Agent suggestion only"

        output += f"Title: {row[0]}\n"
        output += f"Root cause: {best_root}\n"
        output += f"Resolution: {best_fix}\n"
        output += f"Confidence: {verified}\n\n"
    return output