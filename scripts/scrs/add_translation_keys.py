import json
import os
import sys
import concurrent.futures
from pathlib import Path
try:
    from deep_translator import GoogleTranslator
except ImportError:
    print('Installing deep-translator...')
    import subprocess
    subprocess.check_call(['uv', 'pip', 'install', 'deep-translator'])
    from deep_translator import GoogleTranslator
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LANGUAGES = {'zh_CN': {'name': 'Simplified Chinese', 'code': 'zh-CN'}, 'de_DE': {'name': 'German', 'code': 'de'}, 'es_ES': {'name': 'Spanish', 'code': 'es'}, 'fr_FR': {'name': 'French', 'code': 'fr'}, 'ru_RU': {'name': 'Russian', 'code': 'ru'}, 'ja_JP': {'name': 'Japanese', 'code': 'ja'}, 'ko_KR': {'name': 'Korean', 'code': 'ko'}}
NEW_TRANSLATIONS = {
    'edit_pals.search_placeholder': 'Type to filter pals...',
    'edit_pals.nickname_placeholder': 'Optional',
    'deletion.menu.repair_items': 'Repair All Items',
    'deletion.items_repaired': 'Repaired {repaired} items.',
    'edit_pals.bulk_clone': 'Bulk Clone Pals',
    'edit_pals.bulk_delete': 'Bulk Delete Pals',
    'edit_pals.bulk_clone_header': 'Select species to clone',
    'edit_pals.bulk_delete_header': 'Select species to delete',
    'edit_pals.bulk_sources': 'Source:',
    'edit_pals.bulk_clone_apply': 'Clone Selected',
    'edit_pals.bulk_delete_apply': 'Delete Selected',
    'edit_pals.bulk_no_selection': 'No species selected.',
    'edit_pals.bulk_species_cloned': 'Cloned {count} species ({total} pals).',
    'edit_pals.bulk_species_deleted': 'Deleted {count} species ({total} pals).',
    'edit_pals.bulk_clone_confirm': 'Clone all {total} pals from {count} species?',
    'edit_pals.bulk_delete_confirm': 'Delete all {total} pals from {count} species?',
    'edit_pals.bulk_qty': 'Qty',
    'edit_pals.bulk_slots_party': 'Party: {used}/{total}',
    'edit_pals.bulk_slots_palbox': 'Palbox: {used}/{total}',
    'edit_pals.bulk_slots_dps': 'DPS: {free} free',
    'edit_pals.bulk_slots_total': 'Total free: {free}',
    'edit_pals.bulk_footer_requested': 'Requested: {requested} | Available slots: {available}',
    'edit_pals.bulk_not_enough_slots': 'Not enough free slots. Requested {requested}, only {available} available.',
    'xgp.no_saves_found.title': 'No GamePass Saves Found',
    'xgp.no_saves_found.msg': 'Could not find any GamePass save files.\n\nPossible reasons:\n• You have not created a world yet on Xbox Game Pass\n• The save files are in an unreadable format\n\nTry logging into your world on Xbox Game Pass and updating to the latest Palworld version, then try again.',
    'xgp.no_valid_saves.title': 'No Valid Saves Found',
    'xgp.no_valid_saves.msg': 'Your GamePass save data could not be read.\n\nThe container index may be corrupted or from an incompatible version.\n\nTry logging into your world on Xbox Game Pass and updating to the latest Palworld version, then try again.',
    'xgp.save_unreadable.title': 'Save Data Unreadable',
    'xgp.save_unreadable.msg': 'Your GamePass save data could not be read.\n\nThe container index may be corrupted or from an incompatible version.\n\nTry logging into your world on Xbox Game Pass and updating to the latest Palworld version, then try again.',
}
OLD_KEYS = []
def _clean_uv_locks():
    for p in [Path.cwd() / 'uv.lock', PROJECT_ROOT / 'uv.lock']:
        if p.exists():
            p.unlink()

def remove_old_keys_from_all():
    for lang_code in list(LANGUAGES.keys()) + ['en_US']:
        lang_file = PROJECT_ROOT / 'resources' / 'i18n' / f'{lang_code}.json'
        if not lang_file.exists():
            continue
        with open(lang_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        removed = [key for key in OLD_KEYS if data.pop(key, None) is not None]
        with open(lang_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        if removed:
            print(f'  {lang_code}: removed {len(removed)} keys')
def add_english_keys():
    lang_file = PROJECT_ROOT / 'resources' / 'i18n' / 'en_US.json'
    with open(lang_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for key, english_text in NEW_TRANSLATIONS.items():
        data[key] = english_text
    with open(lang_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
def translate_text(text: str, target_lang: str) -> str:
    translator = GoogleTranslator(source='en', target=target_lang)
    return translator.translate(text)
def add_keys_to_language(lang_code: str, lang_info: dict) -> bool:
    try:
        lang_file = PROJECT_ROOT / 'resources' / 'i18n' / f'{lang_code}.json'
        with open(lang_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        had_failure = False
        for key, english_text in NEW_TRANSLATIONS.items():
            try:
                translated = translate_text(english_text, lang_info['code'])
                data[key] = translated
            except Exception as e:
                print(f'  [WARN] {key}: translate failed ({e}), using English fallback')
                data[key] = english_text
                had_failure = True
        with open(lang_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return not had_failure
    except Exception as e:
        print(f'  [ERROR] File-level failure: {e}')
        return False
def main():
    _clean_uv_locks()
    print('\n' + '=' * 60)
    print('  UPDATING TRANSLATION KEYS')
    print('=' * 60)
    print('\nRemoving old keys...')
    remove_old_keys_from_all()
    print('\nEnglish (en_US)...')
    add_english_keys()
    print('  [OK] Success')
    print('\nTranslating to other languages (parallel processing)...')
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(LANGUAGES)) as executor:
        future_to_lang = {executor.submit(add_keys_to_language, lang_code, lang_info): lang_code for lang_code, lang_info in LANGUAGES.items()}
        for future in concurrent.futures.as_completed(future_to_lang):
            lang_code = future_to_lang[future]
            lang_info = LANGUAGES[lang_code]
            try:
                success = future.result()
                print(f"  {lang_info['name']} ({lang_code}): {('[OK] Success' if success else '[ERROR] Failed')}")
            except Exception as e:
                print(f"  {lang_info['name']} ({lang_code}): [ERROR] {e}")
    _clean_uv_locks()
    print('\n' + '=' * 60)
    print('  DONE')
    print('=' * 60)
if __name__ == '__main__':
    main()
