"""Seed 5 demo items per module: Skills, Bounties, Workshop articles."""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.accounts.models import User
from apps.bounties.models import Bounty, BountyType, BountyStatus, WorkloadEstimate
from apps.skills.models import Skill, SkillCategory, SkillStatus, PricingModel
from apps.workshop.models import Article, ArticleDifficulty, ArticleStatus, ArticleType

SKILLS = [
    {
        "name": "Python Code Reviewer",
        "description": "Automatically reviews Python code for style, bugs, and security issues using static analysis.",
        "category": SkillCategory.CODE_DEV,
        "pricing_model": PricingModel.FREE,
        "tags": ["python", "code-review", "static-analysis"],
    },
    {
        "name": "SEO Article Writer",
        "description": "Generates SEO-optimized articles with keyword density analysis and meta description suggestions.",
        "category": SkillCategory.WRITING,
        "pricing_model": PricingModel.PAID,
        "price": "0.50",
        "tags": ["seo", "writing", "content"],
    },
    {
        "name": "CSV Data Analyzer",
        "description": "Analyzes CSV datasets and produces summary statistics, charts, and anomaly detection reports.",
        "category": SkillCategory.DATA_ANALYTICS,
        "pricing_model": PricingModel.PAID,
        "price": "0.30",
        "tags": ["csv", "data", "analytics"],
    },
    {
        "name": "Academic Paper Summarizer",
        "description": "Summarizes academic papers into structured abstracts with key findings and methodology.",
        "category": SkillCategory.ACADEMIC,
        "pricing_model": PricingModel.FREE,
        "tags": ["academic", "summarization", "research"],
    },
    {
        "name": "Productivity Task Planner",
        "description": "Breaks down complex goals into actionable daily tasks with time estimates and priorities.",
        "category": SkillCategory.PRODUCTIVITY,
        "pricing_model": PricingModel.FREE,
        "tags": ["productivity", "planning", "gtd"],
    },
]

BOUNTIES = [
    {
        "title": "Build a Markdown to PDF converter Skill",
        "description": "Need a Skill that converts Markdown documents to well-formatted PDFs with custom styling support. Must handle tables, code blocks, and images.",
        "bounty_type": BountyType.SKILL_CUSTOM,
        "reward": "15.00",
        "workload_estimate": WorkloadEstimate.TWO_TO_THREE_DAYS,
        "skill_requirements": "Python, markdown parsing, PDF generation (reportlab or weasyprint)",
    },
    {
        "title": "Translate 50 product descriptions EN→ZH",
        "description": "Translate 50 e-commerce product descriptions from English to Simplified Chinese. Maintain tone and marketing language.",
        "bounty_type": BountyType.CONTENT_CREATION,
        "reward": "8.00",
        "workload_estimate": WorkloadEstimate.ONE_DAY,
        "skill_requirements": "Native-level Chinese, e-commerce experience preferred",
    },
    {
        "title": "Fix pagination bug in Django Ninja API",
        "description": "Cursor-based pagination returns duplicate items when records are inserted between pages. Reproduce, diagnose, and fix with tests.",
        "bounty_type": BountyType.BUG_FIX,
        "reward": "5.00",
        "workload_estimate": WorkloadEstimate.ONE_TO_TWO_HOURS,
        "skill_requirements": "Django, Django Ninja, PostgreSQL",
    },
    {
        "title": "Scrape and structure AI tool directory",
        "description": "Scrape a public AI tools directory and output structured JSON with name, category, pricing, and description for 200+ tools.",
        "bounty_type": BountyType.DATA_PROCESSING,
        "reward": "12.00",
        "workload_estimate": WorkloadEstimate.HALF_DAY,
        "skill_requirements": "Python, BeautifulSoup or Playwright, JSON",
    },
    {
        "title": "Write onboarding email sequence (5 emails)",
        "description": "Write a 5-email onboarding sequence for a SaaS product targeting AI developers. Tone: friendly, technical, action-oriented.",
        "bounty_type": BountyType.GENERAL,
        "reward": "6.00",
        "workload_estimate": WorkloadEstimate.ONE_DAY,
        "skill_requirements": "Copywriting, SaaS marketing, email best practices",
    },
]

_ARTICLE_CONTENT_1 = (
    "Prompt engineering is the practice of crafting inputs to AI models to "
    "get reliable, high-quality outputs. This guide covers the fundamentals "
    "you need to start building effective prompts.\n\n"
    "## Why Prompt Engineering Matters\n\n"
    "The same model can produce wildly different results depending on how you "
    "phrase your request. A well-engineered prompt can mean the difference "
    "between a generic response and a precisely targeted answer.\n\n"
    "## Core Techniques\n\n"
    "**1. Be Specific About Format**\n"
    'Instead of "summarize this", try "summarize this in 3 bullet points, '
    'each under 20 words, focusing on actionable takeaways."\n\n'
    "**2. Provide Context**\n"
    "Models perform better when they understand the audience and purpose. "
    '"Explain this to a senior Python developer" yields different results '
    'than "explain this to a beginner."\n\n'
    "**3. Use Examples (Few-Shot)**\n"
    "Showing the model 2-3 examples of the input/output pattern you want "
    "dramatically improves consistency.\n\n"
    "**4. Chain of Thought**\n"
    'For complex reasoning tasks, ask the model to "think step by step" '
    "before giving its final answer.\n\n"
    "## Common Pitfalls\n\n"
    "- Ambiguous instructions lead to inconsistent outputs\n"
    "- Overly long prompts can cause the model to lose focus\n"
    "- Not specifying output format forces post-processing\n\n"
    "## Next Steps\n\n"
    "Practice by iterating on a single prompt 10 times, changing one variable "
    "at a time. Track what works."
)

_ARTICLE_CONTENT_2 = (
    "I spent three months manually summarizing research papers for my "
    "literature review. Then I built a pipeline with the Claude API that cut "
    "that time by 80%. Here's exactly what I did.\n\n"
    "## The Problem\n\n"
    "My workflow: download PDF, read abstract, skim methods, note key "
    "findings, add to Notion. For 200 papers, this took roughly 40 hours.\n\n"
    "## The Solution Architecture\n\n"
    "PDF -> text extraction (pdfplumber) -> Claude API -> structured JSON -> "
    "Notion API\n\n"
    "## Key Prompt Design\n\n"
    "The critical insight was asking Claude to output structured JSON rather "
    "than prose. I asked for fields like main_claim (one sentence), "
    "methodology (list), key_findings (3-5 items), limitations, and a "
    "relevance_score from 1-5.\n\n"
    "## Results\n\n"
    "- Processing time per paper: 45 seconds (was 12 minutes)\n"
    "- Accuracy vs manual review: ~85% on key findings\n"
    "- Total cost for 200 papers: ~$4.20\n\n"
    "## What Didn't Work\n\n"
    "First I tried asking for prose summaries. They were good but hard to "
    "compare across papers. Structured output was the unlock.\n\n"
    "## Code\n\n"
    'Full code is available as a Skill on this platform. Search "Research '
    'Paper Analyzer".'
)

_ARTICLE_CONTENT_3 = (
    "Everyone celebrates longer context windows as pure upside. After running "
    "production workloads at scale, I've found the reality is more nuanced.\n\n"
    "## What the Marketing Says\n\n"
    '"1M token context! Fit your entire codebase!" This is technically true '
    "and genuinely useful for some tasks.\n\n"
    "## What Actually Happens at Scale\n\n"
    "**Latency increases non-linearly.** A 100K token prompt doesn't take "
    "10x longer than a 10K prompt — it can take 30-50x longer depending on "
    "the model and infrastructure.\n\n"
    "**Cost scales with input tokens.** If you're stuffing 500K tokens of "
    'context for every query, your costs explode even if the model is "cheap '
    'per token."\n\n'
    "**Quality degrades in the middle.** Research consistently shows models "
    "pay less attention to content in the middle of very long contexts (the "
    '"lost in the middle" problem).\n\n'
    "## When Long Context Is Worth It\n\n"
    "- One-shot analysis tasks where you need the full document\n"
    "- Tasks where retrieval errors are more costly than latency\n"
    "- Offline batch processing where latency doesn't matter\n\n"
    "## Better Alternatives for Most Cases\n\n"
    "1. **RAG (Retrieval Augmented Generation)**: Retrieve only relevant chunks\n"
    "2. **Hierarchical summarization**: Summarize sections, then summarize summaries\n"
    "3. **Structured extraction**: Pull out only the fields you need first\n\n"
    "## The Rule I Use\n\n"
    "If the task can be done with <20K tokens 90% of the time, build for that "
    "case and handle edge cases separately. Don't architect for the worst case."
)

_ARTICLE_CONTENT_4 = (
    "I ran both models through 50 real coding tasks from my work over the "
    "past month. Here's what I found.\n\n"
    "## Test Methodology\n\n"
    "Tasks were drawn from actual work: bug fixes, feature implementations, "
    "refactoring, and code review. Each task was run on both models with "
    "identical prompts. I evaluated on: correctness (does it run?), quality "
    "(would I merge it?), and speed to usable output.\n\n"
    "## Results Summary\n\n"
    "| Category | Claude 3.5 Sonnet | GPT-4o |\n"
    "|----------|-------------------|--------|\n"
    "| Correctness | 88% | 84% |\n"
    "| Code quality | 4.2/5 | 3.9/5 |\n"
    "| Follows instructions | 4.5/5 | 4.1/5 |\n"
    "| Explains reasoning | 4.6/5 | 3.8/5 |\n\n"
    "## Where Claude Wins\n\n"
    "**Long file refactoring**: Claude maintains context better across 500+ "
    "line files and makes more consistent changes throughout.\n\n"
    "**Following constraints**: When I say \"don't use external libraries\" or "
    "\"keep the existing API surface\", Claude respects this more reliably.\n\n"
    "**Code explanation**: Claude's explanations of what it changed and why "
    "are significantly more useful for review.\n\n"
    "## Where GPT-4 Wins\n\n"
    "**Speed**: GPT-4o is noticeably faster for short tasks.\n\n"
    "**Familiarity with obscure libraries**: For niche packages with less "
    "training data, GPT-4 sometimes has better coverage.\n\n"
    "## My Current Setup\n\n"
    "I use Claude for anything requiring careful instruction-following or long "
    "context. GPT-4o for quick one-liners where speed matters."
)

_ARTICLE_CONTENT_5 = (
    "As the CaMeL marketplace grows, we're seeing an interesting tension: "
    "users want stability (lock to a version that works), but also want "
    "improvements (auto-update to latest). How should we think about this?\n\n"
    "## The Problem\n\n"
    "Imagine you've built a workflow that depends on a Skill. The Skill "
    "author releases v2.0 with breaking prompt changes. Your workflow breaks "
    "silently.\n\n"
    "This is the npm left-pad problem, but for AI behavior.\n\n"
    "## Option A: Semantic Versioning (Current Approach)\n\n"
    "Skills use semver. Major version bumps signal breaking changes. Users "
    "can pin to ^1.0.0 or lock to 1.2.3.\n\n"
    "**Pros**: Familiar to developers, explicit contract\n"
    "**Cons**: AI behavior changes are fuzzy — is a 10% quality improvement "
    "a patch or minor?\n\n"
    "## Option B: Behavioral Snapshots\n\n"
    "Instead of versioning the prompt, version the *behavior* by running a "
    "test suite. A new version only ships if it passes all existing "
    "behavioral tests.\n\n"
    "**Pros**: Guarantees backward compatibility\n"
    "**Cons**: Hard to define \"behavioral tests\" for open-ended tasks\n\n"
    "## Option C: Immutable Versions + Deprecation\n\n"
    "Every published version is immutable forever. Authors can deprecate old "
    "versions but never delete them.\n\n"
    "**Pros**: Maximum stability\n"
    "**Cons**: Storage costs, users stuck on bad versions\n\n"
    "## What Do You Think?\n\n"
    "I'm genuinely uncertain which approach is right. The tradeoffs depend "
    "heavily on use case. What's your experience with Skill versioning so far?"
)

ARTICLES = [
    {
        "title": "Getting Started with Prompt Engineering: A Practical Guide",
        "content": _ARTICLE_CONTENT_1,
        "difficulty": ArticleDifficulty.BEGINNER,
        "article_type": ArticleType.TUTORIAL,
        "model_tags": ["claude-3", "gpt-4"],
        "custom_tags": ["prompt-engineering", "beginner"],
    },
    {
        "title": "How I Automated My Research Workflow with Claude API",
        "content": _ARTICLE_CONTENT_2,
        "difficulty": ArticleDifficulty.INTERMEDIATE,
        "article_type": ArticleType.CASE_STUDY,
        "model_tags": ["claude-3-5-sonnet"],
        "custom_tags": ["automation", "research", "api"],
    },
    {
        "title": "The Hidden Cost of Long Context Windows",
        "content": _ARTICLE_CONTENT_3,
        "difficulty": ArticleDifficulty.INTERMEDIATE,
        "article_type": ArticleType.PITFALL,
        "model_tags": ["claude-3", "gpt-4"],
        "custom_tags": ["context-window", "performance", "cost"],
    },
    {
        "title": "Claude vs GPT-4 for Code Generation: A Practical Comparison",
        "content": _ARTICLE_CONTENT_4,
        "difficulty": ArticleDifficulty.INTERMEDIATE,
        "article_type": ArticleType.REVIEW,
        "model_tags": ["claude-3-5-sonnet", "gpt-4o"],
        "custom_tags": ["comparison", "code-generation"],
    },
    {
        "title": "Should AI Skills Have Versioning? A Community Discussion",
        "content": _ARTICLE_CONTENT_5,
        "difficulty": ArticleDifficulty.BEGINNER,
        "article_type": ArticleType.DISCUSSION,
        "model_tags": [],
        "custom_tags": ["versioning", "marketplace", "community"],
    },
]


class Command(BaseCommand):
    help = "Seed 5 demo items per module (Skills, Bounties, Workshop articles)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing seed data before re-seeding (matches usernames seed_user_*).",
        )

    def handle(self, *args, **options):
        with transaction.atomic():
            if options["clear"]:
                User.objects.filter(username__startswith="seed_user_").delete()
                self.stdout.write("Cleared existing seed data.")

            user = self._get_or_create_seed_user()
            self._seed_skills(user)
            self._seed_bounties(user)
            self._seed_articles(user)

        self.stdout.write(self.style.SUCCESS("Seeded 5 skills, 5 bounties, 5 articles."))

    def _get_or_create_seed_user(self):
        user, created = User.objects.get_or_create(
            username="seed_user_demo",
            defaults={
                "email": "demo@camel.community",
                "display_name": "Demo User",
                "credit_score": 500,
                "balance": "100.00",
            },
        )
        if created:
            user.set_password("demo_password_123")
            user.save(update_fields=["password"])
        return user

    def _seed_skills(self, user):
        for data in SKILLS:
            slug = slugify(data["name"])
            skill, created = Skill.objects.get_or_create(
                slug=slug,
                defaults={
                    "creator": user,
                    "name": data["name"],
                    "description": data["description"],
                    "category": data["category"],
                    "pricing_model": data["pricing_model"],
                    "price": data.get("price"),
                    "tags": data["tags"],
                    "status": SkillStatus.APPROVED,
                },
            )
            if created:
                self.stdout.write(f"  Skill: {skill.name}")

    def _seed_bounties(self, user):
        deadline = timezone.now() + timezone.timedelta(days=14)
        for data in BOUNTIES:
            bounty, created = Bounty.objects.get_or_create(
                title=data["title"],
                creator=user,
                defaults={
                    "description": data["description"],
                    "bounty_type": data["bounty_type"],
                    "reward": data["reward"],
                    "workload_estimate": data["workload_estimate"],
                    "skill_requirements": data["skill_requirements"],
                    "status": BountyStatus.OPEN,
                    "deadline": deadline,
                },
            )
            if created:
                self.stdout.write(f"  Bounty: {bounty.title}")

    def _seed_articles(self, user):
        for data in ARTICLES:
            slug = slugify(data["title"])
            article, created = Article.objects.get_or_create(
                slug=slug,
                defaults={
                    "author": user,
                    "title": data["title"],
                    "content": data["content"],
                    "difficulty": data["difficulty"],
                    "article_type": data["article_type"],
                    "model_tags": data["model_tags"],
                    "custom_tags": data["custom_tags"],
                    "status": ArticleStatus.PUBLISHED,
                    "published_at": timezone.now(),
                },
            )
            if created:
                self.stdout.write(f"  Article: {article.title}")
