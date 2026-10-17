import sqlite3
import re
import json
from difflib import SequenceMatcher

# 1. إعداد قاعدة البيانات الشاملة
def init_db():
    conn = sqlite3.connect('master_brain.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_pattern TEXT UNIQUE,
            answer TEXT,
            category TEXT DEFAULT 'عام'
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_keyword TEXT UNIQUE,
            summary_result TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS search_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trigger_keyword TEXT UNIQUE,
            action_instruction TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

# 2. تنظيف النصوص
def clean_text(text):
    text = re.sub(r'[^\w\s]', '', text)
    return " ".join(text.strip().lower().split())

# 3. حساب نسبة التشابه
def similarity_score(a, b):
    seq_score = SequenceMatcher(None, a, b).ratio()
    words_a = set(a.split())
    words_b = set(b.split())
    if not words_a or not words_b:
        jaccard_score = 0.0
    else:
        jaccard_score = len(words_a.intersection(words_b)) / len(words_a.union(words_b))
    return (seq_score * 0.4) + (jaccard_score * 0.6)

# 4. محرك البحث الذكي
def get_learned_answer(user_input):
    conn = sqlite3.connect('master_brain.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT trigger_keyword, action_instruction FROM search_rules")
    rules = cursor.fetchall()
    
    applied_rule = None
    cleaned_input = clean_text(user_input)
    
    for kw, instruction in rules:
        if kw in cleaned_input:
            applied_rule = instruction
            break

    cursor.execute("SELECT question_pattern, answer, category FROM knowledge")
    rows = cursor.fetchall()
    conn.close()

    best_match = None
    best_category = "عام"
    highest_score = 0.0

    for pattern, answer, category in rows:
        score = similarity_score(cleaned_input, clean_text(pattern))
        if score > highest_score:
            highest_score = score
            best_match = answer
            best_category = category

    if highest_score >= 0.40:
        return best_match, highest_score, best_category, applied_rule
    return None, highest_score, None, applied_rule

# 5. تعليم أسلوب وقواعد البحث
def teach_search_rule(keyword, instruction):
    conn = sqlite3.connect('master_brain.db')
    cursor = conn.cursor()
    cleaned_kw = clean_text(keyword)
    try:
        cursor.execute("INSERT INTO search_rules (trigger_keyword, action_instruction) VALUES (?, ?)", (cleaned_kw, instruction))
        print(f"🎯 [أسلوب البحث]: تم حفظ القاعدة للكلمة '{keyword}'")
    except sqlite3.IntegrityError:
        cursor.execute("UPDATE search_rules SET action_instruction = ? WHERE trigger_keyword = ?", (instruction, cleaned_kw))
        print(f"🎯 [أسلوب البحث]: تم تحديث القاعدة للكلمة '{keyword}'")
    conn.commit()
    conn.close()

# 6. تعليم الأسئلة والتلخيصات
def teach_bot(key, value, category="عام", type_mode="qa"):
    conn = sqlite3.connect('master_brain.db')
    cursor = conn.cursor()
    try:
        if type_mode == "qa":
            cursor.execute("INSERT INTO knowledge (question_pattern, answer, category) VALUES (?, ?, ?)", (key, value, category))
            print(f"🤖 [الذكاء الاصطناعي]: تم تعلّم الإجابة ({category}).")
        elif type_mode == "summary":
            cursor.execute("INSERT INTO summaries (source_keyword, summary_result) VALUES (?, ?)", (key, value))
            print("🤖 [الذكاء الاصطناعي]: تم حفظ التلخيص.")
        conn.commit()
    except sqlite3.IntegrityError:
        if type_mode == "qa":
            cursor.execute("UPDATE knowledge SET answer = ?, category = ? WHERE question_pattern = ?", (value, category, key))
        else:
            cursor.execute("UPDATE summaries SET summary_result = ? WHERE source_keyword = ?", (value, key))
        conn.commit()
        print("🤖 [الذكاء الاصطناعي]: تم تحديث الذاكرة بنجاح.")
    conn.close()

# 7. التلخيص الذكي
def get_learned_summary(text):
    conn = sqlite3.connect('master_brain.db')
    cursor = conn.cursor()
    cursor.execute("SELECT source_keyword, summary_result FROM summaries")
    rows = cursor.fetchall()
    conn.close()

    cleaned_text = clean_text(text)
    for keyword, summary in rows:
        if keyword in cleaned_text:
            return summary
    return None

def smart_summarize(text_to_sum):
    saved_summary = get_learned_summary(text_to_sum)
    if saved_summary:
        return f"الذكاء الاصطناعي (من الذاكرة): {saved_summary}", True
    
    sentences = [s.strip() for s in re.split(r'[.؟!;\n]', text_to_sum) if len(s.strip()) > 10]
    if not sentences:
        return f"الخلاصة المبدئية: {text_to_sum}", False
    
    summary_sentences = sentences[:2] if len(sentences) >= 2 else sentences
    auto_summary = "الخلاصة الذكية: " + " ".join(summary_sentences)
    return auto_summary, False

# --- التشغيل الأساسي للنظام ---
init_db()
print("="*65)
print(" نظام الذكاء الاصطناعي المحلي (يتعلم الإجابات والتلخيص) ")
print(" يعمل 100% بدون إنترنت ")
print("="*65)

while True:
    user_input = input("\nأنت: ").strip()
    
    if not user_input:
        continue
        
    if user_input.lower() in ['خروج', 'exit']:
        print("🤖 [الذكاء الاصطناعي]: إلى اللقاء!")
        break

    if user_input.lower() == '/rule':
        kw = input("أدخل الكلمة المفتاحية: ").strip()
        rule = input(f"كيف تفكر عند الكلمة '{kw}'؟: ").strip()
        if kw and rule:
            teach_search_rule(kw, rule)
        continue
    
    if user_input.startswith('لخص') or user_input.startswith('تلخيص'):
        text_to_sum = re.sub(r'^(لخص|تلخيص)\s*', '', user_input).strip()
        if not text_to_sum:
            print("🤖 [الذكاء الاصطناعي]: اكتب النص المراد تلخيصه.")
            continue
            
        summary_output, from_memory = smart_summarize(text_to_sum)
        print(f"🤖 [الذكاء الاصطناعي]: {summary_output}")
        
        if not from_memory:
            feedback = input("هل تريد إعطاء تلخيص أفضل؟ اكتبه هنا (أو اضغط Enter): ").strip()
            if feedback:
                keyword = clean_text(text_to_sum[:25])
                teach_bot(keyword, feedback, type_mode="summary")
        continue

    answer, score, category, applied_rule = get_learned_answer(user_input)
    
    if applied_rule:
        print(f"⚙️ [تطبيق أسلوب البحث]: {applied_rule}")
        
    if answer:
        print(f"🤖 [الذكاء الاصطناعي]: {answer}")
        print(f"   📊 (تصنيف: {category} | المطابقة: {int(score*100)}%)")
    else:
        print("🤖 [الذكاء الاصطناعي]: لم أجد إجابة في الذاكرة.")
        correct_answer = input("علمني الإجابة الصحيحة (أو اضغط Enter للتخطي): ").strip()
        if correct_answer:
            category = input("التصنيف (مثال: عام، تقنية): ").strip() or "عام"
            teach_bot(user_input, correct_answer, category=category, type_mode="qa")
