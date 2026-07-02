"""
agent/workflows/news_pipeline.py
=================================
End-to-end news pipeline workflow.

Orchestrates the full lifecycle from article discovery to publishing:

    1. fetch_tech_news   — RSS ingestion (DynamoDB feed registry + fallback)
    2. check_duplicate   — filter articles already processed in prior runs
    3. summarise         — Amazon Bedrock batch summarisation
    4. generate_post     — platform-specific Bedrock post generation
    5. publish           — fan-out to all enabled publishers
    6. mark_seen         — record processed URLs in DynamoDB to prevent re-posting

Early-exit conditions
---------------------
- Step 2: No new articles after deduplication → pipeline stops, returns empty result.
- Step 3: Bedrock returns no summaries → pipeline stops, returns empty result.

Publisher failures
------------------
A failed publisher does NOT stop the pipeline.  The error is logged and
collected in ``PipelineResult.publish_results``.  Other publishers continue.

Usage::

    import boto3
    from agent.workflows.news_pipeline import NewsPipeline

    pipeline = NewsPipeline(
        dynamodb_client=boto3.client("dynamodb"),
        bedrock_client=boto3.client("bedrock-runtime"),
    )
    result = pipeline.run()
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from agent.config import AgentConfig
from agent.models import ArticleSummary, ContentPackage, PublishResult
from agent.publishers import get_active_publishers
from agent.tools.bedrock_summariser import ArticleSummariser
from agent.tools.deduplication import ArticleDeduplicator
from agent.tools.news_fetcher import NewsFetcher
from agent.tools.post_generator import PostGenerator

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """
    Summary of a single pipeline run.

    Attributes:
        articles_fetched:   Raw article count from RSS feeds.
        articles_new:       Count after deduplication.
        summaries_produced: Count of Bedrock summaries generated.
        publish_results:    One ``PublishResult`` per enabled publisher.
        skipped:            ``True`` if the pipeline exited early (nothing to do).
        skip_reason:        Human-readable reason when ``skipped`` is ``True``.
    """

    articles_fetched: int = 0
    articles_new: int = 0
    summaries_produced: int = 0
    publish_results: list[PublishResult] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str = ""


class NewsPipeline:
    """
    Orchestrates the full tech-news-agent pipeline.

    All AWS clients are injected so the pipeline is fully testable without
    patching module globals or making real AWS calls.

    Args:
        dynamodb_client: ``boto3.client("dynamodb")`` used by fetch + dedup tools.
        bedrock_client:  ``boto3.client("bedrock-runtime")`` used by summariser + generator.
        config:          Agent configuration; defaults to ``AgentConfig``.
        platform:        Post-generation target platform (default ``"linkedin"``).
    """

    def __init__(
        self,
        dynamodb_client: object,
        bedrock_client: object,
        config: type[AgentConfig] = AgentConfig,
        platform: str = "linkedin",
    ) -> None:
        self._config = config
        self._platform = platform
        self._fetcher = NewsFetcher(dynamodb_client=dynamodb_client, config=config)
        self._deduplicator = ArticleDeduplicator(dynamodb_client=dynamodb_client, config=config)
        self._summariser = ArticleSummariser(bedrock_client=bedrock_client, config=config)
        self._generator = PostGenerator(bedrock_client=bedrock_client, config=config)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> PipelineResult:
        """
        Execute the full pipeline and return a ``PipelineResult``.

        The pipeline never raises — all errors are caught, logged, and
        surfaced through ``PipelineResult``.
        """
        result = PipelineResult()

        # ----------------------------------------------------------
        # Step 1: Fetch
        # ----------------------------------------------------------
        logger.info("Pipeline step 1/6: fetching articles")
        articles = self._fetcher.run()
        result.articles_fetched = len(articles)
        logger.info("Fetched %d article(s)", result.articles_fetched)

        # ----------------------------------------------------------
        # Step 2: Deduplicate (filter)
        # ----------------------------------------------------------
        logger.info("Pipeline step 2/6: deduplicating")
        new_articles = self._deduplicator.filter_new(articles)
        result.articles_new = len(new_articles)

        if not new_articles:
            logger.info("No new articles — pipeline exiting early")
            result.skipped = True
            result.skip_reason = "No new articles after deduplication"
            return result

        # ----------------------------------------------------------
        # Step 3: Summarise
        # ----------------------------------------------------------
        logger.info("Pipeline step 3/6: summarising %d article(s)", len(new_articles))
        summaries: list[ArticleSummary] = self._summariser.run(new_articles)
        result.summaries_produced = len(summaries)

        if not summaries:
            logger.warning("Bedrock returned no summaries — pipeline exiting early")
            result.skipped = True
            result.skip_reason = "Bedrock summarisation returned no results"
            return result

        # ----------------------------------------------------------
        # Step 4: Generate post
        # ----------------------------------------------------------
        logger.info("Pipeline step 4/6: generating %s post", self._platform)
        package: ContentPackage = self._generator.run(summaries, platform=self._platform)

        # ----------------------------------------------------------
        # Step 5: Publish
        # ----------------------------------------------------------
        logger.info("Pipeline step 5/6: publishing to enabled platforms")
        publishers = get_active_publishers(self._config.enabled_publishers)

        for publisher in publishers:
            try:
                publish_result = publisher.run(package)
            except Exception as exc:
                logger.exception(
                    "Unexpected error running publisher '%s'", publisher.platform_name
                )
                publish_result = PublishResult(
                    platform=publisher.platform_name,
                    success=False,
                    error=str(exc),
                )
            result.publish_results.append(publish_result)

        # ----------------------------------------------------------
        # Step 6: Mark seen
        # ----------------------------------------------------------
        logger.info("Pipeline step 6/6: recording %d processed article(s)", len(new_articles))
        self._deduplicator.mark_seen(new_articles)

        successes = sum(1 for r in result.publish_results if r.success)
        logger.info(
            "Pipeline complete — %d/%d publishers succeeded",
            successes,
            len(result.publish_results),
        )
        return result
