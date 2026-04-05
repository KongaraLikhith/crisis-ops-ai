# backend/test_search.py
from main import app
from tools.search_tool import search_similar_incidents


def run_search_tests():
    queries = [
        "database connection pool exhausted",
        "auth service login broken 500",
        "payment webhook timeout",
        "email not sending",
        "redis cache eviction causing slow api",
        "s3 uploads failing",
        "completely unrelated thing like spacecraft",  # should ideally return weak/no match
    ]

    with app.app_context():
        print("\n" + "=" * 80)
        print("TESTING SEARCH TOOL (TEXT MODE)")
        print("=" * 80)

        for q in queries:
            print(f"\nQuery: {q}")
            print("-" * 80)
            result = search_similar_incidents(q, limit=3, return_mode="text")
            print(result)

        print("\n" + "=" * 80)
        print("TESTING SEARCH TOOL (JSON MODE)")
        print("=" * 80)

        for q in queries:
            print(f"\nQuery: {q}")
            print("-" * 80)
            result = search_similar_incidents(q, limit=3, return_mode="json")
            for i, row in enumerate(result, start=1):
                print(f"{i}. {row['title']} | score={row.get('similarity_score')} | confidence={row.get('confidence')}")


if __name__ == "__main__":
    run_search_tests()