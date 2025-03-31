# response_generator.py

import os
import re
import logging
from typing import List, Dict, Any, Optional, Tuple, Union
from search_module import SearchResult
from smart_funnel import ReferenceStrategy, MoneySite, SubPage

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Try to import OpenAI for content generation
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    logger.warning("OpenAI library not found. Using fallback content generation.")
    OPENAI_AVAILABLE = False


class ResponseTemplate:
    """Template for structured response generation"""
    
    def __init__(self, name: str, platform: str, complexity: int):
        self.name = name
        self.platform = platform
        self.complexity = complexity  # 1-5
        self.intro_templates = []
        self.main_templates = []
        self.conclusion_templates = []
        self.reference_templates = {
            ReferenceStrategy.TYPE_DIRECT: [],
            ReferenceStrategy.TYPE_INDIRECT: [],
            ReferenceStrategy.TYPE_INFORMATIONAL: [],
            ReferenceStrategy.TYPE_CONTEXTUAL: []
        }
    
    def add_intro(self, template: str) -> None:
        """Add an introduction template"""
        self.intro_templates.append(template)
    
    def add_main(self, template: str) -> None:
        """Add a main content template"""
        self.main_templates.append(template)
    
    def add_conclusion(self, template: str) -> None:
        """Add a conclusion template"""
        self.conclusion_templates.append(template)
    
    def add_reference(self, ref_type: str, template: str) -> None:
        """Add a reference template for a specific type"""
        if ref_type in self.reference_templates:
            self.reference_templates[ref_type].append(template)


# Create platform-specific templates
def create_templates() -> Dict[str, List[ResponseTemplate]]:
    """Create response templates for different platforms and complexity levels"""
    templates = {
        "quora": [],
        "reddit": [],
        "stackexchange": [],
        "default": []
    }
    
    # Quora templates
    for complexity in range(1, 6):
        template = ResponseTemplate("Quora Standard", "quora", complexity)
        
        # Intros
        template.add_intro("Based on my experience, {intro_point}.")
        template.add_intro("I've researched this topic extensively, and {intro_point}.")
        template.add_intro("This is a great question. {intro_point}.")
        
        # Main content
        if complexity <= 2:
            template.add_main("The simple answer is {main_point}.")
            template.add_main("In short, {main_point}.")
        else:
            template.add_main("There are several important factors to consider. First, {main_point}.")
            template.add_main("This is a nuanced topic with multiple aspects. Let me break it down: {main_point}.")
            template.add_main("Let me share a comprehensive answer based on my knowledge: {main_point}.")
        
        # Conclusions
        template.add_conclusion("Hope this helps with your question!")
        template.add_conclusion("Hope this gives you the insight you were looking for.")
        template.add_conclusion("Feel free to ask if you need any clarification.")
        
        # References by type
        template.add_reference(ReferenceStrategy.TYPE_DIRECT, 
                             "I recommend checking out {site_name}'s guide on this: {page_title} ({page_url})")
        template.add_reference(ReferenceStrategy.TYPE_INDIRECT, 
                             "You might find useful information on this topic at {page_url}")
        template.add_reference(ReferenceStrategy.TYPE_INFORMATIONAL, 
                             "According to {site_name}, {reference_info}")
        template.add_reference(ReferenceStrategy.TYPE_CONTEXTUAL, 
                             "I found {page_title} to be quite helpful when researching this topic.")
        
        templates["quora"].append(template)
    
    # Reddit templates
    for complexity in range(1, 6):
        template = ResponseTemplate("Reddit Standard", "reddit", complexity)
        
        # Intros - more conversational for Reddit
        template.add_intro("Hey there! {intro_point}")
        template.add_intro("So I've actually dealt with this before. {intro_point}")
        template.add_intro("I can help with this one. {intro_point}")
        
        # Main content
        if complexity <= 2:
            template.add_main("Basically, {main_point}")
            template.add_main("Short answer: {main_point}")
        else:
            template.add_main("Here's what you need to know: {main_point}")
            template.add_main("Let me break this down for you: {main_point}")
            template.add_main("There are a few things to consider here: {main_point}")
        
        # Conclusions
        template.add_conclusion("Hope that helps!")
        template.add_conclusion("Good luck with everything!")
        template.add_conclusion("Let me know if you have any other questions.")
        
        # References by type - more casual for Reddit, avoiding overt self-promotion
        template.add_reference(ReferenceStrategy.TYPE_DIRECT, 
                             "There's a really good guide about this at {page_url} if you want more info.")
        template.add_reference(ReferenceStrategy.TYPE_INDIRECT, 
                             "I found this resource helpful when I was researching: {page_url}")
        template.add_reference(ReferenceStrategy.TYPE_INFORMATIONAL, 
                             "According to {site_name}, {reference_info}")
        template.add_reference(ReferenceStrategy.TYPE_CONTEXTUAL, 
                             "I came across this guide ({page_title}) that might interest you.")
        
        templates["reddit"].append(template)
    
    # StackExchange templates - more technical and direct
    for complexity in range(1, 6):
        template = ResponseTemplate("StackExchange Standard", "stackexchange", complexity)
        
        # Intros - more technical/direct
        template.add_intro("{intro_point}")
        template.add_intro("To address your question: {intro_point}")
        
        # Main content
        if complexity <= 2:
            template.add_main("{main_point}")
        else:
            template.add_main("Here's a breakdown: {main_point}")
            template.add_main("Several factors to consider: {main_point}")
        
        # Conclusions
        template.add_conclusion("Reference: {page_title} ({page_url})")
        template.add_conclusion("Source: {page_url}")
        
        # References by type - very direct for Stack Exchange
        template.add_reference(ReferenceStrategy.TYPE_DIRECT, 
                             "Reference: {page_title} ({page_url})")
        template.add_reference(ReferenceStrategy.TYPE_INDIRECT, 
                             "For more details: {page_url}")
        template.add_reference(ReferenceStrategy.TYPE_INFORMATIONAL, 
                             "According to {site_name}: {reference_info}")
        template.add_reference(ReferenceStrategy.TYPE_CONTEXTUAL, 
                             "Related resource: {page_title} ({page_url})")
        
        templates["stackexchange"].append(template)
    
    # Default templates (generic)
    for complexity in range(1, 6):
        template = ResponseTemplate("Default", "default", complexity)
        
        # Generic templates
        template.add_intro("Regarding your question, {intro_point}")
        template.add_main("Here's what I can tell you: {main_point}")
        template.add_conclusion("Hope this information helps!")
        
        template.add_reference(ReferenceStrategy.TYPE_DIRECT, 
                             "Check out this resource for more details: {page_url}")
        template.add_reference(ReferenceStrategy.TYPE_INDIRECT, 
                             "You might find this helpful: {page_url}")
        template.add_reference(ReferenceStrategy.TYPE_INFORMATIONAL, 
                             "According to {site_name}, {reference_info}")
        template.add_reference(ReferenceStrategy.TYPE_CONTEXTUAL, 
                             "I found this resource useful: {page_title}")
        
        templates["default"].append(template)
    
    return templates


# Global templates variable
RESPONSE_TEMPLATES = create_templates()


def get_response_template(platform: str, complexity: int) -> ResponseTemplate:
    """
    Get the appropriate response template for a platform and complexity level.
    
    Args:
        platform: The platform name (quora, reddit, etc.)
        complexity: Complexity level (1-5)
        
    Returns:
        The best matching ResponseTemplate
    """
    # Ensure complexity is in valid range
    complexity = max(1, min(5, complexity))
    
    # Get platform-specific templates or default to generic
    platform_templates = RESPONSE_TEMPLATES.get(platform, RESPONSE_TEMPLATES["default"])
    
    # Find the template with matching complexity
    for template in platform_templates:
        if template.complexity == complexity:
            return template
    
    # Fallback to first template in the platform list
    if platform_templates:
        return platform_templates[0]
    
    # Ultimate fallback
    return RESPONSE_TEMPLATES["default"][0]


def get_random_template_text(templates: List[str]) -> str:
    """Get a random template from a list"""
    import random
    if not templates:
        return ""
    return random.choice(templates)


def assemble_response_with_template(template: ResponseTemplate, strategy: ReferenceStrategy,
                                   intro_content: str, main_content: str) -> str:
    """
    Assemble a response using a template and content.
    
    Args:
        template: ResponseTemplate to use
        strategy: ReferenceStrategy with reference info
        intro_content: Content for the introduction
        main_content: Content for the main section
        
    Returns:
        Assembled response text
    """
    # Get template parts
    intro_template = get_random_template_text(template.intro_templates)
    main_template = get_random_template_text(template.main_templates)
    conclusion_template = get_random_template_text(template.conclusion_templates)
    
    # Get reference template based on reference type
    reference_templates = template.reference_templates.get(strategy.reference_type, [])
    reference_template = get_random_template_text(reference_templates)
    
    # Reference data
    site_name = strategy.money_site.name
    page_title = strategy.target_page.title
    page_url = strategy.target_page.url
    
    # Reference information (used in informational references)
    reference_info = f"{page_title} provides detailed guidance on this topic"
    
    # Format the template sections
    intro = intro_template.format(intro_point=intro_content, 
                                 site_name=site_name, 
                                 page_title=page_title,
                                 page_url=page_url,
                                 reference_info=reference_info)
    
    main = main_template.format(main_point=main_content,
                               site_name=site_name,
                               page_title=page_title,
                               page_url=page_url,
                               reference_info=reference_info)
    
    reference = reference_template.format(site_name=site_name,
                                        page_title=page_title,
                                        page_url=page_url,
                                        reference_info=reference_info)
    
    conclusion = conclusion_template.format(site_name=site_name,
                                          page_title=page_title,
                                          page_url=page_url,
                                          reference_info=reference_info)
    
    # Assemble the response based on reference position
    if strategy.reference_position == ReferenceStrategy.POSITION_EARLY:
        response = f"{intro}\n\n{reference}\n\n{main}\n\n{conclusion}"
    elif strategy.reference_position == ReferenceStrategy.POSITION_MIDDLE:
        response = f"{intro}\n\n{main}\n\n{reference}\n\n{conclusion}"
    else:  # POSITION_CONCLUSION
        response = f"{intro}\n\n{main}\n\n{conclusion}\n\n{reference}"
    
    return response


def generate_response_content(question: str, strategy: ReferenceStrategy) -> Tuple[str, str]:
    """
    Generate intro and main content for a response using OpenAI.
    
    Args:
        question: The question to answer
        strategy: ReferenceStrategy with reference info
        
    Returns:
        Tuple of (intro_content, main_content)
    """
    if not OPENAI_AVAILABLE:
        # Fallback content generation
        return (
            "I can provide some insights on this topic.",
            f"Based on my research, there are several important points to consider. {strategy.target_page.content_summary}"
        )
    
    try:
        # Set up system prompt
        system_prompt = f"""
        You are an expert answering a question about "{question}". 
        Create two sections for a response:
        1. A brief introduction (1-2 sentences)
        2. A detailed answer ({strategy.word_count} words)
        
        Use a {strategy.tone} tone appropriate for {strategy.thread.platform}.
        
        Do NOT refer to yourself as an AI. Write as a knowledgeable human.
        
        Include information in your answer about: {strategy.target_page.content_summary}
        
        Format your response as a JSON object with these keys:
        "intro": your introduction
        "main": your detailed answer
        """
        
        # Create the completion
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Question: {question}"}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        response_text = response.choices[0].message["content"]
        
        # Extract JSON
        import json
        import re
        
        # Look for JSON pattern in the response
        json_match = re.search(r'({.*})', response_text, re.DOTALL)
        
        if json_match:
            # Parse the JSON
            response_json = json.loads(json_match.group(1))
            intro_content = response_json.get("intro", "")
            main_content = response_json.get("main", "")
        else:
            # Fallback if JSON extraction fails
            parts = response_text.split("\n\n", 1)
            if len(parts) >= 2:
                intro_content = parts[0].strip()
                main_content = parts[1].strip()
            else:
                intro_content = "Here's some information about your question."
                main_content = response_text
        
        return intro_content, main_content
    
    except Exception as e:
        logger.error(f"Error generating response content: {str(e)}")
        return (
            "I can provide some insights on this topic.",
            f"Based on my research, there are several important points to consider. {strategy.target_page.content_summary}"
        )


def generate_platform_tailored_response(question: str, strategy: ReferenceStrategy) -> str:
    """
    Generate a response tailored to a specific platform.
    
    Args:
        question: The question to answer
        strategy: ReferenceStrategy with reference info
        
    Returns:
        Tailored response text
    """
    # Get the appropriate template
    template = get_response_template(
        platform=strategy.thread.platform,
        complexity=strategy.thread.complexity
    )
    
    # Generate content
    intro_content, main_content = generate_response_content(question, strategy)
    
    # Assemble the response
    response = assemble_response_with_template(
        template=template,
        strategy=strategy,
        intro_content=intro_content,
        main_content=main_content
    )
    
    # Apply platform-specific formatting
    response = format_for_platform(response, strategy.thread.platform)
    
    return response


def format_for_platform(text: str, platform: str) -> str:
    """
    Apply platform-specific formatting to the response.
    
    Args:
        text: The response text
        platform: The target platform
        
    Returns:
        Formatted text
    """
    if platform == "reddit":
        # For Reddit, ensure proper markdown
        # Convert double newlines to Reddit's expected format
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Ensure links are properly formatted
        text = re.sub(r'(?<!\()http(s?)://([\w\.\-/]+)', r'[\2](http\1://\2)', text)
        
    elif platform == "stackexchange":
        # For Stack Exchange, ensure proper markdown
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
    return text


if __name__ == "__main__":
    # Simple test of the response generator
    from search_module import SearchResult
    from smart_funnel import MoneySite, SubPage, ReferenceStrategy
    
    # Create a mock search result
    search_result = SearchResult(
        title="What are the best neighborhoods in Tokyo for expats with families?",
        url="https://www.quora.com/What-are-the-best-neighborhoods-in-Tokyo-for-expats-with-families",
        snippet="I'm moving to Tokyo with my family next year and looking for advice on family-friendly neighborhoods with good international schools.",
        platform="quora"
    )
    
    # Add sample question text and thread content
    search_result.question_text = "What are the best neighborhoods in Tokyo for expats with families?"
    search_result.complexity = 3
    
    # Create mock money site
    money_site = MoneySite(
        name="Living Abroad Guide",
        primary_url="https://livingabroadguide.com",
        categories=["Expat", "Living Abroad", "International Living"]
    )
    
    # Create mock subpage
    subpage = SubPage(
        url="https://livingabroadguide.com/japan/tokyo-neighborhoods/",
        title="Complete Guide to Tokyo Neighborhoods for Expats",
        content_summary="Detailed guide to Tokyo's neighborhoods including Shibuya, Shinjuku, Minato, Setagaya, and more with costs, amenities, and lifestyle factors."
    )
    
    # Create mock strategy
    strategy = ReferenceStrategy(search_result, money_site, subpage)
    strategy.reference_type = ReferenceStrategy.TYPE_INFORMATIONAL
    strategy.reference_position = ReferenceStrategy.POSITION_CONCLUSION
    strategy.word_count = 200
    strategy.tone = "helpful and informative"
    
    # Generate response
    response = generate_platform_tailored_response(search_result.question_text, strategy)
    
    print("Generated Response:\n")
    print(response)
