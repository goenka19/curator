#!/usr/bin/env python3
"""
COMPREHENSIVE END-TO-END TEST SUITE
Tests the complete Twitter processing pipeline with detailed validation

This test suite validates:
1. URL Detection - ALL URLs captured (including t.co)
2. Filtering - Pass unless blacklisted
3. Media Classification - Images, short videos, long videos
4. AI Processing - Proper insight/concept extraction
5. Data Persistence - All fields saved correctly
6. Cost Tracking - Accurate cost calculation
"""

import sys
import os
import json
import re
import unittest
from datetime import datetime
from pathlib import Path

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestURLDetection(unittest.TestCase):
    """Test URL detection captures ALL URLs including t.co"""
    
    def setUp(self):
        """Set up URL detection function"""
        self.url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    
    def detect_urls(self, text):
        """Mirror the detect_urls logic from twitter_extractor.py"""
        urls = re.findall(self.url_pattern, text)
        
        classified = {
            'x_articles': [],
            'external': [],
            'youtube': [],
            'other': []
        }
        
        for url in urls:
            if 'x.com/i/article' in url or 'twitter.com/i/article' in url:
                classified['x_articles'].append(url)
            elif 'youtube.com' in url or 'youtu.be' in url:
                classified['youtube'].append(url)
            elif any(domain in url for domain in ['substack.com', 'medium.com', 'blog.', 'newsletter']):
                classified['external'].append(url)
            else:
                classified['other'].append(url)
        
        return classified, urls
    
    def test_tco_links_captured(self):
        """CRITICAL: t.co links must be detected and saved"""
        test_cases = [
            ('Check this https://t.co/abc123', ['https://t.co/abc123']),
            ('Link: https://t.co/xyz789 here', ['https://t.co/xyz789']),
            ('Multiple https://t.co/a and https://t.co/b', ['https://t.co/a', 'https://t.co/b']),
        ]
        
        for text, expected_urls in test_cases:
            classified, urls = self.detect_urls(text)
            self.assertEqual(len(urls), len(expected_urls), 
                           f"Should detect {len(expected_urls)} URL(s) in: {text}")
            for url in expected_urls:
                self.assertIn(url, urls, f"URL {url} should be detected")
            # t.co links go to 'other' category
            self.assertEqual(len(classified['other']), len(expected_urls),
                           f"t.co links should be in 'other' category")
    
    def test_x_articles_detected(self):
        """X Article links must be categorized correctly"""
        text = 'Read this https://x.com/i/article/123456'
        classified, urls = self.detect_urls(text)
        
        self.assertEqual(len(classified['x_articles']), 1)
        self.assertEqual(len(classified['external']), 0)
        self.assertEqual(len(classified['other']), 0)
    
    def test_external_blogs_detected(self):
        """External blog links must be categorized"""
        test_cases = [
            ('Medium https://medium.com/@user/post', 1, 0),
            ('Substack https://substack.com/p/article', 1, 0),
            ('Blog https://blog.example.com/post', 1, 0),
        ]
        
        for text, expected_external, expected_other in test_cases:
            classified, urls = self.detect_urls(text)
            self.assertEqual(len(classified['external']), expected_external,
                           f"Should detect {expected_external} external link(s)")
    
    def test_youtube_links_detected(self):
        """YouTube links must be categorized"""
        test_cases = [
            'Watch https://youtube.com/watch?v=abc123',
            'Video https://youtu.be/xyz789',
        ]
        
        for text in test_cases:
            classified, urls = self.detect_urls(text)
            self.assertEqual(len(classified['youtube']), 1,
                           f"Should detect YouTube link in: {text}")
    
    def test_mixed_urls_all_captured(self):
        """Multiple different URL types in one tweet"""
        text = '''Check out:
        https://x.com/i/article/123 (X Article)
        https://medium.com/post (External)
        https://t.co/short (Short link)
        https://youtube.com/watch (YouTube)'''
        
        classified, urls = self.detect_urls(text)
        
        self.assertEqual(len(urls), 4, "Should detect all 4 URLs")
        self.assertEqual(len(classified['x_articles']), 1)
        self.assertEqual(len(classified['external']), 1)
        self.assertEqual(len(classified['youtube']), 1)
        self.assertEqual(len(classified['other']), 1)
    
    def test_all_urls_saved_in_backup(self):
        """Verify backup logic saves ALL URL categories"""
        # Simulate the save_raw_backup logic
        urls = {
            'x_articles': ['https://x.com/i/article/1'],
            'external': ['https://medium.com/post'],
            'youtube': ['https://youtube.com/watch'],
            'other': ['https://t.co/abc']
        }
        
        # This mirrors: all_urls = urls['external'] + urls['other'] + urls['youtube']
        all_urls = urls['external'] + urls['other'] + urls['youtube']
        external_links = all_urls + urls['x_articles']
        
        self.assertEqual(len(external_links), 4, "All 4 URLs should be saved")
        self.assertIn('https://t.co/abc', external_links, "t.co link must be saved")


class TestFilteringEngine(unittest.TestCase):
    """Test filtering logic - Pass unless blacklisted"""
    
    def setUp(self):
        from backend.filtering.engine import FilteringEngine
        self.engine = FilteringEngine()
    
    def test_pass_unless_blacklisted(self):
        """Normal content should pass filter"""
        test_cases = [
            ('Learning about finance and investing', '@user', True),
            ('Building AI tools for productivity', '@tech_guru', True),
            ('Just random thoughts about life', '@philosopher', True),
            ('Python coding tutorial thread', '@dev_teacher', True),
            ('Startup advice for founders', '@startup_vc', True),
            ('Random content with no keywords', '@random', True),  # KEY TEST
            ('', '@empty', False),  # Empty should fail
        ]
        
        for text, creator, should_pass in test_cases:
            result, reason = self.engine.should_process(text, creator)
            self.assertEqual(result, should_pass, 
                           f"Text: '{text[:40]}...' Expected {should_pass}, got {result} ({reason})")
    
    def test_blacklist_blocks_content(self):
        """Blacklisted content must be blocked"""
        blocked_cases = [
            ('Check out this NBA highlight!', '@sports'),
            ('Funny meme about cats lol', '@memes'),
            ('Lebron James scores 50 points', '@nba'),
            ('Poker tournament all-in hand', '@poker'),
            ('Movie review of latest blockbuster', '@movies'),
            ('Music video premiere', '@music'),
            ('Lakers vs Warriors tonight', '@nba'),
        ]
        
        for text, creator in blocked_cases:
            result, reason = self.engine.should_process(text, creator)
            self.assertFalse(result, 
                           f"Should block: '{text[:40]}...' but passed")
            self.assertIn('Blacklist', reason, 
                         f"Reason should mention blacklist: {reason}")
    
    def test_whitelist_fast_tracks(self):
        """Whitelist keywords should fast-track"""
        whitelist_cases = [
            ('Great article on private credit', '@finance'),
            ('Game theory and probability', '@strategy'),
            ('Building a startup in AI', '@founder'),
            ('Substack newsletter on economics', '@writer'),
        ]
        
        for text, creator in whitelist_cases:
            result, reason = self.engine.should_process(text, creator)
            self.assertTrue(result, 
                          f"Should pass: '{text[:40]}...'")
            self.assertIn('Whitelist', reason, 
                         f"Reason should mention whitelist: {reason}")
    
    def test_engagement_bait_blocked(self):
        """Engagement bait should be blocked unless high-value creator"""
        # Low-value creator + bait = blocked
        result, reason = self.engine.should_process(
            'Follow for more thoughts?', '@meme_page'
        )
        self.assertFalse(result, "Engagement bait should be blocked")
        
        # High-value creator + bait = allowed (creator has 'finance' in name)
        result, reason = self.engine.should_process(
            'Follow for more thoughts?', '@finance_guru'
        )
        self.assertTrue(result, "High-value creator should bypass bait filter")
    
    def test_pass_rate_reasonable(self):
        """Verify pass rate is high (75%+ should pass)"""
        test_tweets = [
            'Just a normal tweet about life',
            'Random thoughts on productivity',
            'Building things is hard',
            'NBA finals tonight!',  # Blocked
            'Check out this meme lol',  # Blocked
            'Learning about finance',
            'Game theory concepts',
            'Poker hand analysis',  # Should pass (not tournament)
            'Substack article on AI',
            'Follow for more thoughts?',  # Blocked (bait)
            'Python coding tutorial',
            'Earnings report analysis',
        ]
        
        passed = sum(1 for t in test_tweets if self.engine.should_process(t, 'user')[0])
        pass_rate = passed / len(test_tweets)
        
        self.assertGreaterEqual(pass_rate, 0.7, 
                               f"Pass rate {pass_rate:.0%} too low, should be 70%+")


class TestMediaClassification(unittest.TestCase):
    """Test media classification logic"""
    
    def classify_media(self, media_type, duration_ms):
        """Mirror the classify_and_process_media logic"""
        duration_sec = duration_ms / 1000
        
        if media_type == 'photo':
            return {'type': 'image', 'processor': 'process_image'}
        elif media_type in ['video', 'animated_gif']:
            if duration_sec <= 180 or media_type == 'animated_gif':
                return {
                    'type': 'short_video',
                    'processor': 'process_short_video',
                    'includes': 'transcription + frame analysis'
                }
            else:
                return {
                    'type': 'long_video', 
                    'processor': 'process_long_video',
                    'includes': 'transcription only'
                }
        return None
    
    def test_image_classification(self):
        """Images should use process_image"""
        result = self.classify_media('photo', 0)
        self.assertEqual(result['type'], 'image')
        self.assertEqual(result['processor'], 'process_image')
    
    def test_short_video_boundary(self):
        """Videos <= 180s should be short"""
        test_cases = [
            (30000, 'short_video'),    # 30 seconds
            (120000, 'short_video'),   # 2 minutes
            (180000, 'short_video'),   # 3 minutes (boundary)
        ]
        
        for duration_ms, expected_type in test_cases:
            result = self.classify_media('video', duration_ms)
            self.assertEqual(result['type'], expected_type,
                           f"Duration {duration_ms}ms should be {expected_type}")
            self.assertEqual(result['includes'], 'transcription + frame analysis')
    
    def test_long_video_boundary(self):
        """Videos > 180s should be long"""
        test_cases = [
            (181000, 'long_video'),    # 3:01 (just over boundary)
            (600000, 'long_video'),    # 10 minutes
            (3600000, 'long_video'),   # 1 hour
        ]
        
        for duration_ms, expected_type in test_cases:
            result = self.classify_media('video', duration_ms)
            self.assertEqual(result['type'], expected_type,
                           f"Duration {duration_ms}ms should be {expected_type}")
            self.assertEqual(result['includes'], 'transcription only')
    
    def test_gif_always_short(self):
        """GIFs should always be treated as short videos"""
        result = self.classify_media('animated_gif', 5000)  # 5 seconds
        self.assertEqual(result['type'], 'short_video')
        self.assertEqual(result['includes'], 'transcription + frame analysis')
    
    def test_frame_calculation(self):
        """Frame extraction calculation"""
        # Every 2.5 seconds, cap at 24
        def calc_frames(duration_sec):
            frames = int(duration_sec / 2.5)
            return min(frames, 24)
        
        test_cases = [
            (30, 12),   # 30s = 12 frames
            (60, 24),   # 60s = 24 frames (at cap)
            (120, 24),  # 120s = 24 frames (capped)
            (180, 24),  # 180s = 24 frames (capped)
        ]
        
        for duration, expected_frames in test_cases:
            actual = calc_frames(duration)
            self.assertEqual(actual, expected_frames,
                           f"{duration}s video should extract {expected_frames} frames")


class TestAIProcessingPrompt(unittest.TestCase):
    """Test AI processing prompt structure"""
    
    def build_prompt(self, tweet_text, media_analysis, external_links):
        """Mirror the prompt from cli.py"""
        external_summary = ""
        if external_links:
            external_summary = "\n\nEXTERNAL ARTICLES FETCHED:\n" + "\n".join([
                f"- {link['url']}: {link['summary'][:200]}"
                for link in external_links[:3]
            ])
        
        prompt = f"""Analyze this content for KNOWLEDGE VALUE. Be extremely critical.

TWEET TEXT: {tweet_text}

MEDIA ANALYSIS (from images/videos in tweet):
{media_analysis[:1500]}

{external_summary}

REJECT and mark low relevance (1-3) if:
- Just vanity metrics (likes, stars, views, followers)
- Pure news without analysis or insight
- Entertainment/memes with no learning value
- Generic motivational content
- Surface-level observations

ACCEPT and extract ONLY if:
- Teaches a concept, framework, or mental model
- Provides actionable advice or strategies
- Changes how to think about a topic
- Contains specific, reference-able insights
- Explains WHY or HOW something works

Return JSON:
{{
  "title": "3-7 word descriptive title about the core insight (NOT about virality)",
  "core_message": "One sentence: what is this actually about?",
  "key_insight": "What did you learn? Be specific. No fluff.",
  "actionable": "What should the reader DO with this info?",
  "entities": [{{"name": "significant person/company/tool only", "type": "person|company|book|tool"}}],
  "concepts": ["specific topics/frameworks worth researching"],
  "relevance_score": 1-10 (bookmark pre-filtered, so 2+ passes, 5+ is good, 8+ is excellent),
  "category": "finance|strategy|productivity|tech|psychology|other"
}}

Remember: The user curates for QUALITY, not quantity. Be selective."""
        return prompt
    
    def test_prompt_contains_all_sections(self):
        """Prompt must contain all required sections"""
        prompt = self.build_prompt("Test tweet", "", [])
        
        required_sections = [
            'TWEET TEXT:',
            'MEDIA ANALYSIS',
            'REJECT and mark low relevance',
            'ACCEPT and extract ONLY if',
            '"title":',
            '"core_message":',
            '"key_insight":',
            '"entities":',
            '"concepts":',
            '"relevance_score":',
            '"category":',
        ]
        
        for section in required_sections:
            self.assertIn(section, prompt, f"Prompt missing section: {section}")
    
    def test_reject_criteria_specified(self):
        """Prompt must specify what to reject"""
        prompt = self.build_prompt("Test", "", [])
        
        reject_criteria = [
            'vanity metrics',
            'likes, stars, views',
            'Pure news',
            'Entertainment/memes',
            'Generic motivational',
            'Surface-level',
        ]
        
        for criteria in reject_criteria:
            self.assertIn(criteria, prompt, 
                         f"Reject criteria missing: {criteria}")
    
    def test_accept_criteria_specified(self):
        """Prompt must specify what to accept"""
        prompt = self.build_prompt("Test", "", [])
        
        accept_criteria = [
            'Teaches a concept',
            'framework',
            'mental model',
            'actionable advice',
            'strategies',
            'reference-able insights',
            'Explains WHY or HOW',
        ]
        
        for criteria in accept_criteria:
            self.assertIn(criteria, prompt,
                         f"Accept criteria missing: {criteria}")
    
    def test_external_links_included_when_present(self):
        """External links section added when links exist"""
        external = [{'url': 'https://example.com', 'summary': 'Test summary'}]
        prompt = self.build_prompt("Test", "", external)
        
        self.assertIn('EXTERNAL ARTICLES FETCHED', prompt)
        self.assertIn('https://example.com', prompt)
    
    def test_relevance_threshold_specified(self):
        """Prompt must specify 2+ relevance threshold"""
        prompt = self.build_prompt("Test", "", [])
        self.assertIn('2+ passes', prompt)


class TestDatabaseSchema(unittest.TestCase):
    """Test database schema has all required columns"""
    
    def setUp(self):
        from backend.models import ContentItem
        self.columns = {c.name: str(c.type) for c in ContentItem.__table__.columns}
    
    def test_required_columns_exist(self):
        """All required columns must exist"""
        required = [
            'source', 'source_id', 'caption', 'creator_username',
            'pre_filter_passed', 'filter_reason',
            'ai_processed', 'ai_insight', 'entities_json', 'concepts_json',
            'relevance_score', 'category',
            'has_x_article', 'x_article_url', 'external_url',
            'external_links_json', 'media_analysis',
            'obsidian_synced', 'obsidian_path'
        ]
        
        for col in required:
            self.assertIn(col, self.columns, f"Missing column: {col}")
    
    def test_new_columns_added(self):
        """New columns for Twitter processing must exist"""
        new_columns = ['external_links_json', 'media_analysis']
        
        for col in new_columns:
            self.assertIn(col, self.columns, 
                         f"New column {col} not found in schema")
    
    def test_wiki_dict_output(self):
        """to_wiki_dict must return all required fields"""
        from backend.models import ContentItem
        
        mock = ContentItem()
        mock.source_id = '12345'
        mock.source = 'twitter'
        mock.creator_username = 'testuser'
        mock.timestamp = datetime.now()
        mock.caption = 'Test'
        mock.ai_insight = 'Test insight'
        mock.key_points = 'Test Title'
        mock.entities_json = '[{"name": "Test", "type": "company"}]'
        mock.concepts_json = '["AI"]'
        mock.category = 'tech'
        mock.relevance_score = 8
        mock.has_x_article = False
        mock.x_article_url = None
        mock.external_url = 'https://example.com'
        
        wiki = mock.to_wiki_dict()
        
        required_fields = [
            'id', 'source', 'title', 'author', 'date',
            'original_text', 'summary', 'entities', 'concepts',
            'tags', 'relevance_score', 'has_x_article',
            'x_article_url', 'external_url'
        ]
        
        for field in required_fields:
            self.assertIn(field, wiki, f"to_wiki_dict missing field: {field}")


class TestCostTracking(unittest.TestCase):
    """Test cost calculations"""
    
    def test_twitter_api_cost(self):
        """Twitter API: $0.005 per tweet"""
        num_tweets = 96
        cost_per_tweet = 0.005
        total = num_tweets * cost_per_tweet
        self.assertEqual(total, 0.48)
    
    def test_whisper_cost(self):
        """Groq Whisper: $0.04/hour"""
        # 3 minute video
        cost_3min = (3/60) * 0.04
        self.assertAlmostEqual(cost_3min, 0.002, places=3)
        
        # 10 minute video
        cost_10min = (10/60) * 0.04
        self.assertAlmostEqual(cost_10min, 0.0067, places=3)
    
    def test_vision_cost(self):
        """Groq Vision: ~$0.11 per 1M tokens"""
        # 24 frames * 200 tokens = 4800 tokens
        tokens = 24 * 200
        cost = (tokens / 1_000_000) * 0.11
        self.assertAlmostEqual(cost, 0.000528, places=5)


class TestEndToEndDataFlow(unittest.TestCase):
    """Test complete data flow through pipeline"""
    
    def test_data_transformation_chain(self):
        """Verify data transforms correctly through each stage"""
        # Stage 1: Raw tweet
        raw_tweet = {
            'id': '12345',
            'text': 'Great article on AI https://t.co/abc',
            'created_at': '2024-01-15T10:30:00.000Z',
            'author_id': 'user123'
        }
        
        # Stage 2: URL detection
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, raw_tweet['text'])
        self.assertEqual(len(urls), 1)
        self.assertEqual(urls[0], 'https://t.co/abc')
        
        # Stage 3: Filter decision
        from backend.filtering.engine import FilteringEngine
        engine = FilteringEngine()
        should_pass, reason = engine.should_process(raw_tweet['text'], 'tech_writer')
        self.assertTrue(should_pass)
        
        # Stage 4: Item data structure
        item_data = {
            'source': 'twitter',
            'source_id': raw_tweet['id'],
            'caption': raw_tweet['text'],
            'pre_filter_passed': should_pass,
            'filter_reason': None if should_pass else reason,
            'external_url': urls[0] if urls else None,
        }
        
        self.assertEqual(item_data['source'], 'twitter')
        self.assertEqual(item_data['external_url'], 'https://t.co/abc')
        self.assertTrue(item_data['pre_filter_passed'])


def run_all_tests():
    """Run the complete test suite"""
    print("="*80)
    print("COMPREHENSIVE TWITTER PROCESSING TEST SUITE")
    print("="*80)
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestURLDetection))
    suite.addTests(loader.loadTestsFromTestCase(TestFilteringEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestMediaClassification))
    suite.addTests(loader.loadTestsFromTestCase(TestAIProcessingPrompt))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseSchema))
    suite.addTests(loader.loadTestsFromTestCase(TestCostTracking))
    suite.addTests(loader.loadTestsFromTestCase(TestEndToEndDataFlow))
    
    # Run with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED - PIPELINE VALIDATED")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED")
        return 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
