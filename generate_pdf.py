"""Generate a PDF menu from the Micro Bread & Co. menu data."""

import weasyprint

HTML_CONTENT = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  @page {
    size: A4;
    margin: 0;
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    font-family: Georgia, 'Times New Roman', serif;
    background: #1a1510;
    color: #f0e6d6;
    padding: 40px;
  }

  header {
    text-align: center;
    padding: 30px 20px 25px;
    border-bottom: 1px solid rgba(212, 180, 131, 0.3);
    margin-bottom: 20px;
  }

  header h1 {
    font-size: 42pt;
    letter-spacing: 8px;
    text-transform: uppercase;
    color: #e8d5b7;
    font-weight: 700;
  }

  header p {
    font-size: 10pt;
    letter-spacing: 4px;
    text-transform: uppercase;
    color: #a09080;
    margin-top: 4px;
  }

  .section-title {
    font-size: 16pt;
    text-align: center;
    padding: 20px 0 12px;
    color: #c4a97d;
    letter-spacing: 4px;
    text-transform: uppercase;
    border-top: 1px solid rgba(212, 180, 131, 0.15);
    margin-top: 10px;
  }

  .menu-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 14px;
    justify-content: center;
    padding-bottom: 10px;
  }

  .card {
    background: #252017;
    border-radius: 12px;
    border: 1px solid rgba(212, 180, 131, 0.12);
    width: 240px;
    overflow: hidden;
    page-break-inside: avoid;
  }

  .card-emoji {
    width: 100%;
    height: 100px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 48px;
    background: linear-gradient(135deg, #3a2e1f 0%, #2a2218 100%);
  }

  .card-body {
    padding: 14px;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 6px;
  }

  .card-name {
    font-size: 12pt;
    font-weight: 700;
    color: #e8d5b7;
    flex: 1;
    margin-right: 8px;
    line-height: 1.3;
  }

  .tag {
    font-family: Helvetica, Arial, sans-serif;
    font-size: 6pt;
    font-weight: 700;
    letter-spacing: 1px;
    padding: 2px 6px;
    border-radius: 3px;
    text-transform: uppercase;
    display: inline-block;
    margin-left: 4px;
    vertical-align: middle;
  }

  .tag-v { background: #2d4a2d; color: #8bc48b; }
  .tag-vg { background: #1e4a3a; color: #6bc4a4; }
  .tag-s { background: #4a3a1e; color: #c4a46b; }

  .card-price {
    font-size: 14pt;
    font-weight: 700;
    color: #c4a97d;
    flex-shrink: 0;
  }

  .card-desc {
    font-family: Helvetica, Arial, sans-serif;
    font-size: 8pt;
    color: #9a8a78;
    line-height: 1.6;
    font-weight: 300;
  }

  .addons-section {
    max-width: 420px;
    margin: 0 auto;
    padding: 5px 20px 20px;
  }

  .addon-row {
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    border-bottom: 1px solid rgba(212, 180, 131, 0.08);
    font-family: Helvetica, Arial, sans-serif;
    font-size: 9pt;
  }

  .addon-row span:last-child {
    color: #c4a97d;
    font-weight: 600;
  }

  .footer {
    text-align: center;
    padding: 20px;
    font-family: Helvetica, Arial, sans-serif;
    font-size: 7pt;
    color: #6a5a4a;
    letter-spacing: 1px;
  }
</style>
</head>
<body>

<header>
  <h1>Micro</h1>
  <p>Bread &amp; Co.</p>
</header>

<div class="section-title">Entrées</div>
<div class="menu-grid">

  <div class="card">
    <div class="card-emoji">🍳</div>
    <div class="card-body">
      <div class="card-header">
        <span class="card-name">Baker's Breakfast</span>
        <span class="card-price">$28</span>
      </div>
      <p class="card-desc">Pork sausage · scrambled free range eggs · roasted mushrooms · fresh tomato · brie with hot honey · herb butter · sourdough</p>
    </div>
  </div>

  <div class="card">
    <div class="card-emoji">🐟</div>
    <div class="card-body">
      <div class="card-header">
        <span class="card-name">Smoked Salmon Tartine</span>
        <span class="card-price">$23</span>
      </div>
      <p class="card-desc">Tzatziki · cucumber · alfalfa · pomegranate · horseradish</p>
    </div>
  </div>

  <div class="card">
    <div class="card-emoji">🍅</div>
    <div class="card-body">
      <div class="card-header">
        <span class="card-name">Tomato Tartine <span class="tag tag-v">V</span></span>
        <span class="card-price">$17</span>
      </div>
      <p class="card-desc">Tomato on vine · cherry tomatoes · ricotta · basil</p>
    </div>
  </div>

  <div class="card">
    <div class="card-emoji">🥑</div>
    <div class="card-body">
      <div class="card-header">
        <span class="card-name">Avocado Tartine <span class="tag tag-v">V</span></span>
        <span class="card-price">$19</span>
      </div>
      <p class="card-desc">Edamame · beetroot · feta · pickled shallot · radish · zaatar</p>
    </div>
  </div>

  <div class="card">
    <div class="card-emoji">🥚</div>
    <div class="card-body">
      <div class="card-header">
        <span class="card-name">Slow Cooked Eggs &amp; Toast</span>
        <span class="card-price">$16</span>
      </div>
      <p class="card-desc">Onion soubise · bacon bits · kailan</p>
    </div>
  </div>

  <div class="card">
    <div class="card-emoji">🫕</div>
    <div class="card-body">
      <div class="card-header">
        <span class="card-name">Shakshuka <span class="tag tag-v">V</span></span>
        <span class="card-price">$18</span>
      </div>
      <p class="card-desc">Baked eggs · crunchy chickpea · tomato · bell pepper · salsa verde · sourdough</p>
    </div>
  </div>

  <div class="card">
    <div class="card-emoji">🍆</div>
    <div class="card-body">
      <div class="card-header">
        <span class="card-name">Brinjal Flatbread <span class="tag tag-vg">VG</span></span>
        <span class="card-price">$18</span>
      </div>
      <p class="card-desc">Cashew cream · pistachio · dukkah · citrus</p>
    </div>
  </div>

  <div class="card">
    <div class="card-emoji">🥪</div>
    <div class="card-body">
      <div class="card-header">
        <span class="card-name">Breakfast Sando</span>
        <span class="card-price">$16</span>
      </div>
      <p class="card-desc">Spam · scrambled free range eggs · tomato · relish · chipotle mayo · milk toast</p>
    </div>
  </div>

  <div class="card">
    <div class="card-emoji">🧀</div>
    <div class="card-body">
      <div class="card-header">
        <span class="card-name">Grilled 4 Cheese <span class="tag tag-v">V</span></span>
        <span class="card-price">$16</span>
      </div>
      <p class="card-desc">Raclette · smoked ricotta · mozzarella · cheddar · tomato jam</p>
    </div>
  </div>

  <div class="card">
    <div class="card-emoji">🧀</div>
    <div class="card-body">
      <div class="card-header">
        <span class="card-name">Grilled 4 Cheese w/ Kimchi</span>
        <span class="card-price">$18</span>
      </div>
      <p class="card-desc">Raclette · smoked ricotta · mozzarella · cheddar · sauerkraut · tomato jam</p>
    </div>
  </div>

</div>

<div class="section-title">Small Bites / Toast</div>
<div class="menu-grid">

  <div class="card">
    <div class="card-emoji">🍍</div>
    <div class="card-body">
      <div class="card-header">
        <span class="card-name">Ricotta &amp; Pineapple Toast <span class="tag tag-v">V</span> <span class="tag tag-s">Seasonal</span></span>
        <span class="card-price">$13</span>
      </div>
      <p class="card-desc">Pickled pineapple · pineapple jam · toasted almond · pepper berry sea salt · mint</p>
    </div>
  </div>

  <div class="card">
    <div class="card-emoji">🥜</div>
    <div class="card-body">
      <div class="card-header">
        <span class="card-name">House Nut Butter Toast <span class="tag tag-v">V</span></span>
        <span class="card-price">$9</span>
      </div>
      <p class="card-desc">Almond · hazelnut · sunflower seeds · honey</p>
    </div>
  </div>

  <div class="card">
    <div class="card-emoji">🥣</div>
    <div class="card-body">
      <div class="card-header">
        <span class="card-name">Granola <span class="tag tag-v">V</span></span>
        <span class="card-price">$12</span>
      </div>
      <p class="card-desc">Cocoa granola · yoghurt · fresh fruits · honey</p>
    </div>
  </div>

  <div class="card">
    <div class="card-emoji">🍞</div>
    <div class="card-body">
      <div class="card-header">
        <span class="card-name">Bread &amp; Butter Plate</span>
        <span class="card-price">$8</span>
      </div>
      <p class="card-desc">Two slices sourdough · butter</p>
    </div>
  </div>

</div>

<div class="section-title">Add-ons</div>
<div class="addons-section">
  <div class="addon-row"><span>Scrambled Free Range Eggs</span><span>$6</span></div>
  <div class="addon-row"><span>Sunny Side</span><span>$5</span></div>
  <div class="addon-row"><span>Avocado</span><span>$4</span></div>
  <div class="addon-row"><span>Mushroom</span><span>$5</span></div>
  <div class="addon-row"><span>Burrata</span><span>$8</span></div>
  <div class="addon-row"><span>Pork Sausage</span><span>$7</span></div>
  <div class="addon-row"><span>Homemade Jam</span><span>$1</span></div>
</div>

<div class="footer">
  V — Vegetarian &nbsp;&nbsp;/&nbsp;&nbsp; VG — Vegan &nbsp;&nbsp;|&nbsp;&nbsp; Prices are GST inclusive
</div>

</body>
</html>
"""

weasyprint.HTML(string=HTML_CONTENT).write_pdf("menu_with_images.pdf")
print("PDF generated: menu_with_images.pdf")
