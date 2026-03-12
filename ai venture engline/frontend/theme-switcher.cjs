const fs = require('fs');
const path = require('path');

const directoryPath = path.join(__dirname, 'src');

const replacements = [
  // Backgrounds
  { regex: /bg-zinc-950/g, replacement: 'bg-slate-50' },
  { regex: /bg-zinc-900\/50/g, replacement: 'bg-white shadow-sm' },
  { regex: /bg-zinc-900\/40/g, replacement: 'bg-white shadow-sm' },
  { regex: /bg-zinc-900\/60/g, replacement: 'bg-white shadow-sm' },
  { regex: /bg-zinc-900\/80/g, replacement: 'bg-white shadow-sm' },
  { regex: /bg-zinc-900/g, replacement: 'bg-white' },
  { regex: /bg-zinc-800\/50/g, replacement: 'bg-slate-50' },
  { regex: /bg-zinc-800/g, replacement: 'bg-slate-100' },
  // Text colors
  { regex: /text-zinc-50/g, replacement: 'text-slate-900' },
  { regex: /text-white/g, replacement: 'text-slate-900' },
  { regex: /text-zinc-100/g, replacement: 'text-slate-800' },
  { regex: /text-zinc-300/g, replacement: 'text-slate-700' },
  { regex: /text-zinc-400/g, replacement: 'text-slate-600' },
  { regex: /text-zinc-500/g, replacement: 'text-slate-500' },
  // Borders
  { regex: /border-zinc-800\/50/g, replacement: 'border-slate-200' },
  { regex: /border-zinc-800\/60/g, replacement: 'border-slate-200' },
  { regex: /border-zinc-800\/80/g, replacement: 'border-slate-200' },
  { regex: /border-zinc-800/g, replacement: 'border-slate-200' },
  { regex: /border-zinc-700/g, replacement: 'border-slate-300' },
  { regex: /border-zinc-900/g, replacement: 'border-slate-200' },
  // Hovers
  { regex: /hover:bg-zinc-800\/50/g, replacement: 'hover:bg-slate-50' },
  { regex: /hover:bg-zinc-800/g, replacement: 'hover:bg-slate-100' },
  { regex: /hover:bg-zinc-900\/80/g, replacement: 'hover:bg-slate-50' },
  { regex: /hover:bg-zinc-200/g, replacement: 'hover:bg-indigo-50' },
  // specific components exceptions (buttons that shouldn't be dark text)
  { regex: /bg-indigo-600 text-slate-900/g, replacement: 'bg-indigo-600 text-white' },
  { regex: /bg-white text-zinc-950/g, replacement: 'bg-indigo-50 text-indigo-700' }
];

function processFile(filePath) {
  let content = fs.readFileSync(filePath, 'utf8');
  let original = content;

  replacements.forEach(({ regex, replacement }) => {
    content = content.replace(regex, replacement);
  });

  // Fix buttons where text-slate-900 overrides necessary white text
  content = content.replace(/bg-indigo-600(.*?)text-slate-900/g, 'bg-indigo-600$1text-white');
  content = content.replace(/text-slate-900(.*?)bg-indigo-600/g, 'text-white$1bg-indigo-600');
  
  // Specific fix for Landing Page gradient text
  content = content.replace(/text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-400/g, 'text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-purple-600');
  
  // Specific fix for dark gradients
  content = content.replace(/from-indigo-900\/20/g, 'from-indigo-500\/10');
  content = content.replace(/from-purple-900\/20/g, 'from-purple-500\/10');
  content = content.replace(/bg-indigo-900\/20/g, 'bg-indigo-500\/10');
  content = content.replace(/bg-purple-900\/20/g, 'bg-purple-500\/10');

  if (content !== original) {
    fs.writeFileSync(filePath, content, 'utf8');
    console.log(`Updated: ${filePath}`);
  }
}

function traverseDirectory(dir) {
  fs.readdirSync(dir).forEach(file => {
    const fullPath = path.join(dir, file);
    if (fs.statSync(fullPath).isDirectory()) {
      traverseDirectory(fullPath);
    } else if (fullPath.endsWith('.jsx')) {
      processFile(fullPath);
    }
  });
}

traverseDirectory(directoryPath);
console.log('Theme conversion complete.');
