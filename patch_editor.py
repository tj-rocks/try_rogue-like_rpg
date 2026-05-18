import re

with open("tools/village_editor.html", "r") as f:
    content = f.read()

# Change mapData to baseMapData and entityMapData
content = content.replace("let mapData = [];", "let baseMapData = [];\nlet entityMapData = [];\nlet activeLayer = 'base'; // 'base' or 'entity'")

# Modify exportToText
export_func_old = """function exportToText() {
  const lines = document.getElementById('raw-text').value.split('\\n');
  const comments = lines.filter(l => l.startsWith('//') || l.trim() === '').map(l => l.replace(/\\r/,''));

  const mapLines = mapData.map(rowArr => rowArr.join(''));
  const output = [...comments, ...mapLines].join('\\n');
  document.getElementById('raw-text').value = output;
  return output;
}"""

export_func_new = """function exportToText() {
  const lines = document.getElementById('raw-text').value.split('\\n');
  const comments = lines.filter(l => l.startsWith('//') || l.trim() === '').map(l => l.replace(/\\r/,''));

  const mapLines = baseMapData.map(rowArr => rowArr.join(''));
  const output = [...comments, ...mapLines].join('\\n');
  document.getElementById('raw-text').value = output;
  return output;
}"""
content = content.replace(export_func_old, export_func_new)

# Modify renderFromText
render_func_old = """function renderFromText() {
  const text = document.getElementById('raw-text').value;
  const lines = text.split('\\n');
  mapData = [];
  lines.forEach(line => {
    if (line.startsWith('//')) return; // コメント行はスキップ
    if (line.trim() === '') return;     // 空行もスキップ
    mapData.push(Array.from(line.replace(/\\r/,'')));
  });
  drawGrid();
}"""

render_func_new = """function renderFromText() {
  const text = document.getElementById('raw-text').value;
  const lines = text.split('\\n');
  baseMapData = [];
  entityMapData = [];
  
  lines.forEach((line, ri) => {
    if (line.startsWith('//')) return; // コメント行はスキップ
    if (line.trim() === '') return;     // 空行もスキップ
    
    let baseRow = [];
    let entityRow = [];
    
    Array.from(line.replace(/\\r/,'')).forEach((ch, ci) => {
        const t = TILE[ch];
        if (t && t[6] && (t[6] === 'npc' || t[6] === 'obstacle')) {
            // It's an entity. Push to entity map, and fallback base map to floor
            entityRow.push(ch);
            // Guess background based on bgImgPath string
            if (t[5] && t[5].includes('floor_1')) {
                baseRow.push(','); // Indoors floor
            } else {
                baseRow.push('.'); // Outdoors grass
            }
        } else {
            // Normal base tile
            entityRow.push(null);
            baseRow.push(ch);
        }
    });
    
    baseMapData.push(baseRow);
    entityMapData.push(entityRow);
  });
  drawGrid();
}"""
content = content.replace(render_func_old, render_func_new)

# Modify drawGrid
drawGrid_old = """  mapData.forEach((rowArr, ri) => {
    const rowDiv = document.createElement('div');
    rowDiv.style.display = 'block';
    rowDiv.style.lineHeight = '0';

    rowArr.forEach((ch, ci) => {"""

drawGrid_new = """  baseMapData.forEach((rowArr, ri) => {
    const rowDiv = document.createElement('div');
    rowDiv.style.display = 'block';
    rowDiv.style.lineHeight = '0';

    rowArr.forEach((baseCh, ci) => {
      const entCh = entityMapData[ri][ci];
      const ch = entCh ? entCh : baseCh;
"""
content = content.replace(drawGrid_old, drawGrid_new)

content = content.replace("mapData.length === 0", "baseMapData.length === 0")
content = content.replace("mapData[0]?.length", "baseMapData[0]?.length")
content = content.replace("mapData.length", "baseMapData.length")

# Modify setCell
setcell_old = """function setCell(ri, ci, ch, cell) {
  if (!mapData[ri] || ci >= mapData[ri].length) return;
  mapData[ri][ci] = ch;"""

setcell_new = """function setCell(ri, ci, ch, cell) {
  if (!baseMapData[ri] || ci >= baseMapData[ri].length) return;
  
  const t = TILE[ch];
  const isEntity = t && t[6] && (t[6] === 'npc' || t[6] === 'obstacle');
  const isEraser = (ch === '.');
  
  if (isEntity) {
      entityMapData[ri][ci] = ch;
  } else {
      if (isEraser && entityMapData[ri][ci]) {
          // Erase entity instead of base tile if an entity exists
          entityMapData[ri][ci] = null;
      } else {
          baseMapData[ri][ci] = ch;
      }
  }
  
  const entCh = entityMapData[ri][ci];
  const baseCh = baseMapData[ri][ci];
  const finalCh = entCh ? entCh : baseCh;
  ch = finalCh;
"""
content = content.replace(setcell_old, setcell_new)

# Modify clearAll
clear_old = """function clearAll() {
  if (confirm('マップグリッドとテキストをクリアしますか？')) {
    mapData = [];"""
clear_new = """function clearAll() {
  if (confirm('マップグリッドとテキストをクリアしますか？')) {
    baseMapData = [];
    entityMapData = [];"""
content = content.replace(clear_old, clear_new)


# Add category to TILE data in JS
# Look for: TILE[char] = [bg, fg, desc, id, image_path, bg_image_path];
fetch_old = """TILE[char] = [bg, fg, desc, id, image_path, bg_image_path];"""
fetch_new = """TILE[char] = [bg, fg, desc, id, image_path, bg_image_path, tile.category];"""
content = content.replace(fetch_old, fetch_new)


# Modify saveToServer to send entityData
savetoServer_old = """function saveToServer() {
  const fileContent = exportToText();
  const serverStatus = document.getElementById('server-status');
  serverStatus.textContent = '⏳ 保存中...';
  serverStatus.style.color = '#eab308';
  
  fetch('/save_village', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content: fileContent, filename: currentFilename })
  })"""

savetoServer_new = """function saveToServer() {
  const fileContent = exportToText();
  const serverStatus = document.getElementById('server-status');
  serverStatus.textContent = '⏳ 保存中...';
  serverStatus.style.color = '#eab308';
  
  let entities = [];
  for (let r = 0; r < entityMapData.length; r++) {
    for (let c = 0; c < entityMapData[r].length; c++) {
        if (entityMapData[r][c]) {
            entities.push({
                char: entityMapData[r][c],
                x: c,
                y: r
            });
        }
    }
  }
  
  fetch('/save_village', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content: fileContent, filename: currentFilename, entities: entities })
  })"""
content = content.replace(savetoServer_old, savetoServer_new)

with open("tools/village_editor.html", "w") as f:
    f.write(content)
