import json, logging

def save_rule_result(
        conn,
        pr_id: int, 
        rule_result: dict
    ):
    with conn.cursor() as cursor:
        
        try:
            insert_query = """
            INSERT INTO rule_check_logs (
                pr_id,
                matched_rules,
                violation_count
            )
            VALUES (%s, %s, %s)
            """

            cursor.execute(
                insert_query,
                (
                    pr_id,
                    json.dumps(rule_result.get("matched_rules", [])),
                    rule_result.get("violation_count", 0)
                )
            )
            conn.commit()
        except Exception as e:
            logging.error(e)
        finally:
            cursor.close()
