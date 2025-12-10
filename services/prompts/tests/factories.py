import factory
from factory.fuzzy import FuzzyText, FuzzyInteger, FuzzyChoice
from prompt_manager.models.orm import Prompt, PromptVersion, Tag, PromptTag, LLMConfig
import datetime

class PromptFactory(factory.Factory):
    class Meta:
        model = Prompt

    id = factory.Faker('uuid4')
    name = factory.Faker('slug')
    created_at = factory.LazyFunction(datetime.datetime.now)
    updated_at = factory.LazyFunction(datetime.datetime.now)

class PromptVersionFactory(factory.Factory):
    class Meta:
        model = PromptVersion

    id = factory.Faker('uuid4')
    prompt_id = factory.Faker('uuid4')
    version = "1.0"
    version_number = 1
    description = factory.Faker('sentence')
    is_active = True
    is_latest = True
    created_at = factory.LazyFunction(datetime.datetime.now)
    # Relationships
    prompt = factory.SubFactory(PromptFactory)

class LLMConfigFactory(factory.Factory):
    class Meta:
        model = LLMConfig

    id = factory.Faker('uuid4')
    model = "gpt-4"
    temperature = 0.7
    max_tokens = 1000
    top_p = 1.0
    version_id = factory.Faker('uuid4')

class TagFactory(factory.Factory):
    class Meta:
        model = Tag

    id = factory.Faker('uuid4')
    name = factory.Faker('word')
