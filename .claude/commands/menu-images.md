You have been given an image of a restaurant or cafe menu. Your job is to create a visual version of the menu with images for every food and drink item.

## Steps

1. **Read the menu image** at the path provided in $ARGUMENTS. Use the Read tool to view it. If no path is provided, ask the user to provide the image path.

2. **Extract every item** from the menu. For each item, note:
   - Item name
   - Price (if visible)
   - Description (if visible)

3. **Search for an image of each item.** For every food or drink item, use WebSearch to search for something like `"[item name] food photo"` or `"[item name] drink photo"`. Then use WebFetch on the image search results to find a direct image URL. Pick the most appetizing, representative photo.

4. **Generate an HTML file** called `menu_with_images.html` in the current directory. The HTML should:
   - Have a clean, modern design with a dark or warm background
   - Show each menu item as a card with:
     - The item image (as an `<img>` tag with the found URL)
     - Item name in bold
     - Price
     - Description (if available)
   - Use a responsive grid layout (CSS grid, 2-3 columns)
   - Group items by category/section if the menu has sections
   - Include a title at the top with the restaurant name if visible on the menu

5. **Open or report** the generated file path so the user can view it in a browser.

## Important
- Search for EVERY item, not just a few. Be thorough.
- If a search doesn't return a good image, try alternative search terms (e.g., add "restaurant", "plated", or the cuisine type).
- Use real image URLs from the search results, not placeholder images.
- Make the HTML self-contained (inline CSS, no external dependencies).
