#!/usr/bin/env python3
"""
Test filtering engine with Twitter bookmark examples
"""

from backend.filtering.engine import FilteringEngine

def test_twitter_bookmarks():
    engine = FilteringEngine()

    test_cases = [
        # Should SKIP - NBA
        ("Lakers beat the Celtics in overtime!", "sports_fan"),
        ("LeBron with another triple double", "nba_updates"),
        ("Warriors playoff game tonight", "basketball_news"),

        # Should SKIP - Poker games
        ("Just went all-in with pocket aces at WSOP", "poker_player"),
        ("River card saved me in this tournament", "poker_daily"),

        # Should KEEP - Poker strategy
        ("Expected value in poker and decision making in business", "strategy_guy"),
        ("Game theory and probability in investing", "quant_trader"),

        # Should KEEP - Finance
        ("Great article on private credit markets", "finance_insider"),
        ("This company's earnings report is fascinating", "investor"),

        # Should KEEP - Books & Learning
        ("Must read book recommendation on economics", "book_reviewer"),
        ("Lesson learned from building my startup", "founder"),
        ("Insightful article on Substack about AI", "tech_writer"),

        # Should SKIP - Memes
        ("This is so funny lol", "meme_lord"),
        ("Tag a friend who needs to see this", "viral_content"),
    ]

    print("=" * 80)
    print("Twitter Bookmark Filtering Test")
    print("=" * 80)
    print()

    passed = 0
    filtered = 0

    for text, creator in test_cases:
        should_process, reason = engine.should_process(text, creator)
        status = "✅ KEEP" if should_process else "❌ SKIP"
        print(f"{status} | {text[:50]:<50} | {reason}")

        if should_process:
            passed += 1
        else:
            filtered += 1

    print()
    print("=" * 80)
    print(f"Results: {passed} kept, {filtered} filtered ({filtered/(passed+filtered)*100:.1f}% reduction)")
    print("=" * 80)

if __name__ == "__main__":
    test_twitter_bookmarks()
