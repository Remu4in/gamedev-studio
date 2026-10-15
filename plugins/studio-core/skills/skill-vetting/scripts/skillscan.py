"""Статический сканер скиллов/агентов. НЕ выводит тело файлов — только метаданные,
флаги риска и заголовки (repr, обрезанные). Использование: python3 -I skillscan.py <root> <file>..."""
import re, sys, os, unicodedata, json

INVISIBLE = re.compile('[​-‏‪-‮⁠-⁤⁦-⁩﻿\U000e0000-\U000e007f]')
FLAGS = {
    'shell_pipe_exec': r'(curl|wget|iwr|irm|Invoke-WebRequest)[^\n]{0,80}\|\s*(ba)?sh|\|\s*iex',
    'download_cmd': r'\b(curl|wget|Invoke-WebRequest|iwr|irm)\b',
    'base64': r'base64|frombase64|atob\(|b64decode',
    'long_b64_blob': r'[A-Za-z0-9+/]{120,}={0,2}',
    'eval_exec': r'\beval\b|\bexec\(|os\.system|subprocess|OS\.execute',
    'destructive': r'rm\s+-rf|del\s+/[sq]|format\s+c:|Remove-Item[^\n]*-Recurse',
    'secrets_access': r'\.env\b|id_rsa|\.ssh|credentials|api[_-]?key|token',
    'net_exfil_words': r'webhook|exfil|ngrok|pastebin|requestbin|discord(app)?\.com/api',
    'injection_phrases': r'ignore (all |any )?(previous|prior|above)|disregard (the|all)|you are now|developer mode|do not (tell|mention|reveal)|hidden instruction|system prompt',
    'memory_writes': r'CLAUDE\.md|MEMORY\.md|SOUL\.md|\.claude/(settings|memory)',
    'scheduling': r'CronCreate|crontab|schtasks|ScheduleWakeup',
    'skill_chaining': r'\bSkill\(|invoke (the )?skill|/[a-z-]+ skill',
    'bypass_perms': r'bypassPermissions|dangerously|--no-verify|skip(ping)? permission',
    'html_comment': r'<!--',
}
FM_KEYS = ('name','description','tools','allowed-tools','disallowedTools','model','permissionMode','hooks','mcpServers','skills','effort','memory','user-invocable','when_to_use','disable-model-invocation','context','background','isolation')

def scan(path):
    raw = open(path, 'rb').read()
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError:
        return {'file': path, 'error': 'not utf-8'}
    res = {'file': os.path.relpath(path, ROOT), 'bytes': len(raw), 'lines': text.count('\n') + 1}
    inv = INVISIBLE.findall(text)
    res['invisible_chars'] = len(inv)
    other_ctrl = [c for c in text if unicodedata.category(c) in ('Cc', 'Cf') and c not in '\n\r\t']
    res['control_or_format_chars'] = len(other_ctrl)
    fm = {}
    m = re.match(r'^---\n(.*?)\n---\n', text, re.S)
    if m:
        for line in m.group(1).splitlines():
            k = line.split(':', 1)[0].strip()
            if k in FM_KEYS and k not in ('description',):
                v = line.split(':', 1)[1].strip() if ':' in line else ''
                fm[k] = repr(v[:80])
            elif k and not line.startswith((' ', '\t', '-')) and k not in FM_KEYS:
                fm['UNKNOWN_KEY:' + k[:30]] = ''
        res['description_len'] = len(re.search(r'^description:(.*)$', m.group(1), re.M).group(1)) if re.search(r'^description:', m.group(1), re.M) else 0
    res['frontmatter'] = fm
    flags = {}
    for name, rx in FLAGS.items():
        n = len(re.findall(rx, text, re.I))
        if n:
            flags[name] = n
    res['flags'] = flags
    res['urls_domains'] = sorted(set(re.findall(r'https?://([^/\s)>\]"\']+)', text)))
    res['code_blocks'] = text.count('```') // 2
    res['max_line_len'] = max(len(l) for l in text.splitlines()) if text else 0
    res['headings'] = [repr(h[:70]) for h in re.findall(r'^#{1,4} (.+)$', text, re.M)][:40]
    return res

ROOT = sys.argv[1]
for f in sys.argv[2:]:
    print(json.dumps(scan(os.path.join(ROOT, f)), ensure_ascii=False))
