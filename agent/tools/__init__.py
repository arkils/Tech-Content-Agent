"""
agent/tools/__init__.py
=======================
AgentCore tool definitions package.

Each module in this package exposes one or more tools that the agent can invoke
as part of its reasoning loop. Tools are registered with AWS AgentCore and must
conform to the AgentCore tool-call contract.

TODO:
    - Implement news_fetcher tool (RSS / News API ingestion).
    - Implement deduplication tool (DynamoDB lookup).
    - Implement bedrock_summariser tool.
    - Implement linkedin_publisher tool.
    - Register all tools in the AgentCore tool registry.
"""
