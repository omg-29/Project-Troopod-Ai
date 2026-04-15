import asyncio
import json
import logging
from app.services.prompt_engine import generate_master_prompt
from app.services.code_modifier import modify_page
from app.schemas import TextRequirements, ImageAnalysis, ImageMetadata, ScrapedPage

logging.basicConfig(level=logging.INFO)

async def test_enrichment_and_safety():
    print("\n--- Testing Enrichment & Injection Safety ---")
    
    # 1. Mock Data: Sparse text + Rich image data
    text_req = TextRequirements(
        exact_keywords=["gaming laptop"],
        specific_details="sell this laptop" # Very sparse
    )
    
    image_analysis = ImageAnalysis(
        main_product="UltraCore G15 Gaming Laptop",
        target_audience="Competitive gamers and creators",
        deal_extracted="30% Off Student Discount - Use code GAMER30",
        metadata=ImageMetadata(
            color_palette="Neon Green and Carbon Black",
            typography_style="Bold Tech Sans-serif",
            brand_name="UltraCore",
            urgency_signals="Limited quantities available",
            visual_elements="RGB keyboard, sleek chassis",
            text_overlays="30% OFF | ULTRACORE G15"
        )
    )
    
    # Simple mockup HTML
    html = "<html><body><div id='hero'><h1>Old Headline</h1><button class='cta'>Buy</button></div></body></html>"
    a11y_tree = {"role": "RootWebArea", "name": "Test Page"}
    theme = {"backgroundColor": "rgb(255, 255, 255)", "color": "rgb(0, 0, 0)", "variables": {"--primary": "#22c55e"}}

    # 2. Test Step 4a: Enrichment
    print("\nStep 4a: Generating Enriched Master Prompt...")
    master_prompt = await generate_master_prompt(text_req, image_analysis, a11y_tree, theme)
    print(f"Master Prompt:\n{master_prompt}")
    
    # Check for volume (6-7 items) and enrichment (details from image)
    lines = [l for l in master_prompt.split('\n') if l.strip()]
    print(f"Number of instruction markers: {master_prompt.count('1.') + master_prompt.count('2.') + master_prompt.count('3.') + master_prompt.count('4.') + master_prompt.count('5.') + master_prompt.count('6.')}")
    assert "UltraCore" in master_prompt or "30%" in master_prompt
    
    # 3. Test Step 4b: Injection Safety
    print("\nStep 4b: Modifying Page with Safety Styles...")
    scraped_page = ScrapedPage(
        cleaned_html=html,
        css_bundle="",
        js_bundle="",
        accessibility_tree=a11y_tree,
        screenshot_base64="",
        visual_theme=theme,
        base_url="https://example.com"
    )
    
    modified = await modify_page(master_prompt, scraped_page)
    
    print("\nVerifying Injections...")
    # Look for the safety styles in the modified HTML
    has_safety = "z-index: 9999" in modified.html or "display: block !important" in modified.html
    print(f"Found Safety Styles: {has_safety}")
    
    if not has_safety:
        # Check if the AI used add_css instead
        has_safety_css = "z-index: 9999" in modified.css or "display: block" in modified.css
        print(f"Found Safety in CSS additions: {has_safety_css}")
        has_safety = has_safety or has_safety_css

    assert has_safety, "Injection safety styles missing from output!"
    print("\nTEST PASSED: Enrichment and Safety are working.")

if __name__ == "__main__":
    asyncio.run(test_enrichment_and_safety())
