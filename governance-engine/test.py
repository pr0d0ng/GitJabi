import json
from traceback import format_exc
from dotenv import load_dotenv
from governance_engine.engine import GovernanceEngine
from governance_engine.modules.psql import DatabasePool

load_dotenv()



def main():
    # 🔹 sample_pr.json에는 GitHub webhook payload 형태가 들어있다고 가정
    with open("sample_pr.json", "r", encoding="utf-8") as f:
        payload = json.load(f)

    result = None
    db_pool = None
    try:
        #--------------------
        #       DB 연결
        #--------------------
        db_pool = DatabasePool()

        #--------------------
        #       엔진 시작
        #--------------------
        print("=== Running Governance Engine ===")
        with db_pool.get_connection() as conn:
            engine = GovernanceEngine(conn)
            try:
                result = engine.run(payload)
            except Exception as e:
                print(f"[ERROR] {e} \n {format_exc()}")
                return
    except Exception as e:
        print(e)
    finally:
        if db_pool:
            db_pool.close_all()

    print("\nEnd of Task.")
    with open('./debug/result.json', 'w', encoding='utf-8') as fn:
        fn.write(json.dumps(result, indent=4, ensure_ascii=False))


if __name__ == "__main__":
    main()