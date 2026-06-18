#!/usr/bin/env python3
"""
自动为所有语言文件添加跨块冗余校验与纠错功能的翻译
"""

import json
import os

# 基础路径
LOCALES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src", "i18n", "locales")

# 新增的GUI翻译键（需要为每个语言提供翻译）
GUI_TRANSLATIONS = {
    "setting_enable_redundancy": {
        "ja_jp": "クロスブロック誤り訂正を有効にする",
        "ko_kp": "크로스 블록 오류 수정 사용",
        "ko_kr": "크로스 블록 오류 수정 사용", 
        "de_de": "Fehlerkorrektur über Blöcke hinweg aktivieren",
        "es_es": "Activar corrección de errores entre bloques",
        "fr": "Activer la correction d'erreurs entre blocs",
        "it_it": "Attiva correzione errori tra blocchi",
        "pt_br": "Ativar correção de erros entre blocos",
        "ru_ru": "Включить межблочную коррекцию ошибок",
        "tr": "Bloklar arası hata düzeltmeyi etkinleştir",
        "da_dk": "Aktiver tværblock-fejlkorrektion",
        "he_il": "אפשר תיקון שגיאות בין בלוקים",
        "hi_in": "क्रॉस-ब्लॉक त्रुटि सुधार सक्षम करें",
        "th_th": "เปิดใช้งานการแก้ไขข้อผิดพลาดข้ามบล็อก",
        "ug_cn": "تىزما ئارا خاتالىق تۈزىتىشنى قوزغات",
        "uk_ua": "Увімкнути міжблокову корекцію помилок",
        "vi_vn": "Bật sửa lỗi giữa các khối",
        "bo": "སྡེབ་གཅིག་གི་ནོར་འཁྲུལ་སྐྱོན་བཅོས་སྒྲིག་སྤར་བའི།",
    },
    "setting_rs_strength": {
        "ja_jp": "誤り訂正強度",
        "ko_kp": "오류 수정 강도",
        "ko_kr": "오류 수정 강도",
        "de_de": "Fehlerkorrekturstärke",
        "es_es": "Intensidad de corrección de errores",
        "fr": "Force de correction d'erreurs",
        "it_it": "Intensità correzione errori",
        "pt_br": "Intensidade de correção de erros",
        "ru_ru": "Сила коррекции ошибок",
        "tr": "Hata düzeltme gücü",
        "da_dk": "Fejlkorrektionsstyrke",
        "he_il": "עוצמת תיקון שגיאות",
        "hi_in": "त्रुटि सुधार शक्ति",
        "th_th": "ความแรงของการแก้ไขข้อผิดพลาด",
        "ug_cn": "خاتالىق تۈزىتىش كۈچى",
        "uk_ua": "Сила корекції помилок",
        "vi_vn": "Độ mạnh sửa lỗi",
        "bo": "ནོར་འཁྲུལ་སྐྱོན་བཅོས་སྒྲིག་གི་སྟོབས་ཤུགས།",
    },
    "rs_strength_low": {
        "ja_jp": "低 (2%)",
        "ko_kp": "낮음 (2%)",
        "ko_kr": "낮음 (2%)",
        "de_de": "Niedrig (2%)",
        "es_es": "Bajo (2%)",
        "fr": "Faible (2%)",
        "it_it": "Basso (2%)",
        "pt_br": "Baixo (2%)",
        "ru_ru": "Низкий (2%)",
        "tr": "Düşük (2%)",
        "da_dk": "Lav (2%)",
        "he_il": "נמוך (2%)",
        "hi_in": "कम (2%)",
        "th_th": "ต่ำ (2%)",
        "ug_cn": "تۆۋەن (2%)",
        "uk_ua": "Низький (2%)",
        "vi_vn": "Thấp (2%)",
        "bo": "དམའ་བ། (2%)",
    },
    "rs_strength_medium": {
        "ja_jp": "中 (5%)",
        "ko_kp": "중간 (5%)",
        "ko_kr": "중간 (5%)",
        "de_de": "Mittel (5%)",
        "es_es": "Medio (5%)",
        "fr": "Moyen (5%)",
        "it_it": "Medio (5%)",
        "pt_br": "Médio (5%)",
        "ru_ru": "Средний (5%)",
        "tr": "Orta (5%)",
        "da_dk": "Medium (5%)",
        "he_il": "בינוני (5%)",
        "hi_in": "मध्यम (5%)",
        "th_th": "ปานกลาง (5%)",
        "ug_cn": "ئوتتۇرا (5%)",
        "uk_ua": "Середній (5%)",
        "vi_vn": "Trung bình (5%)",
        "bo": "འབྲིང་བ། (5%)",
    },
    "rs_strength_high": {
        "ja_jp": "高 (10%)",
        "ko_kp": "높음 (10%)",
        "ko_kr": "높음 (10%)",
        "de_de": "Hoch (10%)",
        "es_es": "Alto (10%)",
        "fr": "Élevé (10%)",
        "it_it": "Alto (10%)",
        "pt_br": "Alto (10%)",
        "ru_ru": "Высокий (10%)",
        "tr": "Yüksek (10%)",
        "da_dk": "Høj (10%)",
        "he_il": "גבוה (10%)",
        "hi_in": "उच्च (10%)",
        "th_th": "สูง (10%)",
        "ug_cn": "يۇقىرى (10%)",
        "uk_ua": "Високий (10%)",
        "vi_vn": "Cao (10%)",
        "bo": "མཐོ་བ། (10%)",
    },
    "redundancy_info": {
        "ja_jp": "回復可能な破損QRコード: {max_recoverable}/{total}",
        "ko_kp": "복구 가능한 손상된 QR 코드: {max_recoverable}/{total}",
        "ko_kr": "복구 가능한 손상된 QR 코드: {max_recoverable}/{total}",
        "de_de": "Wiederherstellbare beschädigte QR-Codes: {max_recoverable}/{total}",
        "es_es": "Códigos QR dañados recuperables: {max_recoverable}/{total}",
        "fr": "Codes QR endommagés récupérables: {max_recoverable}/{total}",
        "it_it": "Codici QR danneggiati recuperabili: {max_recoverable}/{total}",
        "pt_br": "Códigos QR danificados recuperáveis: {max_recoverable}/{total}",
        "ru_ru": "Восстанавливаемые поврежденные QR-коды: {max_recoverable}/{total}",
        "tr": "Kurtarılabilir hasarlı QR kodları: {max_recoverable}/{total}",
        "da_dk": "Gendannelige beskadigede QR-koder: {max_recoverable}/{total}",
        "he_il": "קודי QR פגומים שניתן לשחזר: {max_recoverable}/{total}",
        "hi_in": "पुनर्प्राप्त करने योग्य क्षतिग्रस्त QR कोड: {max_recoverable}/{total}",
        "th_th": "สามารถกู้คืน QR โค้ดที่เสียหายได้: {max_recoverable}/{total}",
        "ug_cn": "ئەسلىگە كەلتۈرگىلى بولىدىغان بۇزۇلغان QR كودى: {max_recoverable}/{total}",
        "uk_ua": "Відновлювані пошкоджені QR-коди: {max_recoverable}/{total}",
        "vi_vn": "Mã QR hỏng có thể khôi phục: {max_recoverable}/{total}",
        "bo": "སླར་གསོ་བྱེད་ཐུབ་པའི་སྡེབ་གཅིག་གི་QRསྐད་འཕྲིན་རྒྱབ་འཁྲུལ། {max_recoverable}/{total}",
    },
}

# 新增的auto_split_qr翻译键
AUTO_SPLIT_QR_TRANSLATIONS = {
    "redundancy_enabled": {
        "ja_jp": "   - 冗長性訂正: 有効 (冗長ブロック数: {redundancy_blocks}, 回復可能: {max_recoverable})",
        "ko_kp": "   - 중복성 수정: 사용 (중복 블록 수: {redundancy_blocks}, 복구 가능: {max_recoverable})",
        "ko_kr": "   - 중복성 수정: 사용 (중복 블록 수: {redundancy_blocks}, 복구 가능: {max_recoverable})",
        "de_de": "   - Redundanzkorrektur: Aktiviert (Redundanzblöcke: {redundancy_blocks}, Wiederherstellbar: {max_recoverable})",
        "es_es": "   - Corrección de redundancia: Activada (bloques redundantes: {redundancy_blocks}, recuperable: {max_recoverable})",
        "fr": "   - Correction de redondance: Activée (blocs redondants: {redundancy_blocks}, récupérable: {max_recoverable})",
        "it_it": "   - Correzione ridondanza: Abilitata (blocchi ridondanti: {redundancy_blocks}, recuperabile: {max_recoverable})",
        "pt_br": "   - Correção de redundância: Ativada (blocos redundantes: {redundancy_blocks}, recuperável: {max_recoverable})",
        "ru_ru": "   - Коррекция избыточности: Включено (избыточные блоки: {redundancy_blocks}, восстанавливаемо: {max_recoverable})",
        "tr": "   - Artıklık düzeltme: Etkin (artıklık blokları: {redundancy_blocks}, kurtarılabilir: {max_recoverable})",
        "da_dk": "   - Redundanskorrektion: Aktiveret (redundante blokke: {redundancy_blocks}, gendannelig: {max_recoverable})",
        "he_il": "   - תיקון יתירות: מופעל (בלוקי יתירות: {redundancy_blocks}, ניתן לשחזור: {max_recoverable})",
        "hi_in": "   - प्रतिकृति सुधार: सक्षम (प्रतिकृति ब्लॉक: {redundancy_blocks}, पुनर्प्राप्त करने योग्य: {max_recoverable})",
        "th_th": "   - การแก้ไขความซ้ำซ้อน: เปิดใช้งาน (บล็อกซ้ำ: {redundancy_blocks}, กู้คืนได้: {max_recoverable})",
        "ug_cn": "   - ئارتۇقچە تۈزىتىش: قوزغىتىلدى (ئارتۇقچە بىرەك: {redundancy_blocks}, ئەسلىگە كەلتۈرگىلى بولىدۇ: {max_recoverable})",
        "uk_ua": "   - Корекція надлишковості: Увімкнено (надлишкові блоки: {redundancy_blocks}, відновлюється: {max_recoverable})",
        "vi_vn": "   - Sửa lỗi dư thừa: Đã bật (khối dư thừa: {redundancy_blocks}, có thể khôi phục: {max_recoverable})",
        "bo": "   - སྡེབ་གཅིག་གི་སྐྱོན་བཅོས་སྒྲིག་སྤར་བའི།: སྤར་བའི། (སྡེབ་གཅིག་གི་སྐྱོན་བཅོས་སྒྲིག་སྤར་བའི།: {redundancy_blocks}, སླར་གསོ་བྱེད་ཐུབ་པ།: {max_recoverable})",
    },
    "redundancy_disabled": {
        "ja_jp": "   - 冗長性訂正: 無効",
        "ko_kp": "   - 중복성 수정: 사용 안 함",
        "ko_kr": "   - 중복성 수정: 사용 안 함",
        "de_de": "   - Redundanzkorrektur: Deaktiviert",
        "es_es": "   - Corrección de redundancia: Desactivada",
        "fr": "   - Correction de redondance: Désactivée",
        "it_it": "   - Correzione ridondanza: Disabilitata",
        "pt_br": "   - Correção de redundância: Desativada",
        "ru_ru": "   - Коррекция избыточности: Отключено",
        "tr": "   - Artıklık düzeltme: Devre dışı",
        "da_dk": "   - Redundanskorrektion: Deaktiveret",
        "he_il": "   - תיקון יתירות: מושבת",
        "hi_in": "   - प्रतिकृति सुधार: अक्षम",
        "th_th": "   - การแก้ไขความซ้ำซ้อน: ปิดใช้งาน",
        "ug_cn": "   - ئارتۇقچە تۈزىتىش: چەكلەنگەن",
        "uk_ua": "   - Корекція надлишковості: Вимкнено",
        "vi_vn": "   - Sửa lỗi dư thừa: Đã tắt",
        "bo": "   - སྡེབ་གཅིག་གི་སྐྱོན་བཅོས་སྒྲིག་སྤར་བའི།: སྤར་བའི།",
    },
    "rs_encoding_done": {
        "ja_jp": "   - Reed-Solomonエンコーディング完了",
        "ko_kp": "   - Reed-Solomon 인코딩 완료",
        "ko_kr": "   - Reed-Solomon 인코딩 완료",
        "de_de": "   - Reed-Solomon-Codierung abgeschlossen",
        "es_es": "   - Codificación Reed-Solomon completada",
        "fr": "   - Encodage Reed-Solomon terminé",
        "it_it": "   - Codifica Reed-Solomon completata",
        "pt_br": "   - Codificação Reed-Solomon concluída",
        "ru_ru": "   - Кодирование Reed-Solomon завершено",
        "tr": "   - Reed-Solomon kodlaması tamamlandı",
        "da_dk": "   - Reed-Solomon kodning færdig",
        "he_il": "   - קידוד Reed-Solomon הושלם",
        "hi_in": "   - Reed-Solomon एन्कोडिंग पूर्ण",
        "th_th": "   - การเข้ารหัส Reed-Solomon เสร็จสมบูรณ์",
        "ug_cn": "   - Reed-Solomon كودلاش تامام",
        "uk_ua": "   - Кодування Reed-Solomon завершено",
        "vi_vn": "   - Mã hóa Reed-Solomon hoàn tất",
        "bo": "   - Reed-Solomon ཀོཌིང་བརྒྱབ་འཁྲུལ་སྒྲིག་སྤར་བའི།",
    },
}

# 新增的scanner_decoder翻译键
SCANNER_DECODER_TRANSLATIONS = {
    "crc_check_passed": {
        "ja_jp": "   - CRC32チェック: ✓ 合格",
        "ko_kp": "   - CRC32 검사: ✓ 통과",
        "ko_kr": "   - CRC32 검사: ✓ 통과",
        "de_de": "   - CRC32-Prüfung: ✓ Bestanden",
        "es_es": "   - Verificación CRC32: ✓ Aprobada",
        "fr": "   - Vérification CRC32: ✓ Réussie",
        "it_it": "   - Verifica CRC32: ✓ Passata",
        "pt_br": "   - Verificação CRC32: ✓ Aprovada",
        "ru_ru": "   - Проверка CRC32: ✓ Прошла",
        "tr": "   - CRC32 kontrolü: ✓ Başarılı",
        "da_dk": "   - CRC32-tjek: ✓ Bestået",
        "he_il": "   - בדיקת CRC32: ✓ עברה",
        "hi_in": "   - CRC32 जाँच: ✓ पास",
        "th_th": "   - การตรวจสอบ CRC32: ✓ ผ่าน",
        "ug_cn": "   - CRC32 تەكشۈرۈش: ✓ ئۆتتى",
        "uk_ua": "   - Перевірка CRC32: ✓ Пройдена",
        "vi_vn": "   - Kiểm tra CRC32: ✓ Đạt",
        "bo": "   - CRC32 ཞིབ་བཤེར།: ✓ འགྲུབ་པ།",
    },
    "crc_check_failed": {
        "ja_jp": "   - CRC32チェック: ✗ 失敗 (チャンクID: {chunk_ids})",
        "ko_kp": "   - CRC32 검사: ✗ 실패 (청크 ID: {chunk_ids})",
        "ko_kr": "   - CRC32 검사: ✗ 실패 (청크 ID: {chunk_ids})",
        "de_de": "   - CRC32-Prüfung: ✗ Fehlgeschlagen (Chunk-IDs: {chunk_ids})",
        "es_es": "   - Verificación CRC32: ✗ Fallida (IDs de chunk: {chunk_ids})",
        "fr": "   - Vérification CRC32: ✗ Échouée (IDs de chunk: {chunk_ids})",
        "it_it": "   - Verifica CRC32: ✗ Fallita (ID chunk: {chunk_ids})",
        "pt_br": "   - Verificação CRC32: ✗ Falhou (IDs dos chunks: {chunk_ids})",
        "ru_ru": "   - Проверка CRC32: ✗ Неудачно (ID чанков: {chunk_ids})",
        "tr": "   - CRC32 kontrolü: ✗ Başarısız (küme kimlikleri: {chunk_ids})",
        "da_dk": "   - CRC32-tjek: ✗ Fejlet (chunk-ID'er: {chunk_ids})",
        "he_il": "   - בדיקת CRC32: ✗ נכשלה (מזהי חלקים: {chunk_ids})",
        "hi_in": "   - CRC32 जाँच: ✗ विफल (चंक आईडी: {chunk_ids})",
        "th_th": "   - การตรวจสอบ CRC32: ✗ ล้มเหลว (รหัสชิ้นส่วน: {chunk_ids})",
        "ug_cn": "   - CRC32 تەكشۈرۈش: ✗ مەغلۇب بولدى (بۆلەك ID: {chunk_ids})",
        "uk_ua": "   - Перевірка CRC32: ✗ Невдала (ID чанків: {chunk_ids})",
        "vi_vn": "   - Kiểm tra CRC32: ✗ Thất bại (ID khối: {chunk_ids})",
        "bo": "   - CRC32 ཞིབ་བཤེར།: ✗ མ་འགྲུབ་པ། (སྡེབ་གཅིག་གི་པར་རིས་གྱི་ID: {chunk_ids})",
    },
    "missing_chunks": {
        "ja_jp": "   - 欠落チャンク: {missing_chunks}",
        "ko_kp": "   - 누락된 청크: {missing_chunks}",
        "ko_kr": "   - 누락된 청크: {missing_chunks}",
        "de_de": "   - Fehlende Chunks: {missing_chunks}",
        "es_es": "   - Chunks faltantes: {missing_chunks}",
        "fr": "   - Chunks manquants: {missing_chunks}",
        "it_it": "   - Chunk mancanti: {missing_chunks}",
        "pt_br": "   - Chunks ausentes: {missing_chunks}",
        "ru_ru": "   - Отсутствующие чанки: {missing_chunks}",
        "tr": "   - Eksik kümeler: {missing_chunks}",
        "da_dk": "   - Manglende chunks: {missing_chunks}",
        "he_il": "   - חלקים חסרים: {missing_chunks}",
        "hi_in": "   - अनुपस्थित चंक: {missing_chunks}",
        "th_th": "   - ชิ้นส่วนที่ขาดหาย: {missing_chunks}",
        "ug_cn": "   - يوقاپ كەتكەن بۆلەك: {missing_chunks}",
        "uk_ua": "   - Відсутні чанки: {missing_chunks}",
        "vi_vn": "   - Các khối bị thiếu: {missing_chunks}",
        "bo": "   - སྡེབ་གཅིག་གི་པར་རིས་རྒྱབ་འཁྲུལ།: {missing_chunks}",
    },
    "total_corrupted": {
        "ja_jp": "   - 総破損チャンク数: {corrupted_count}",
        "ko_kp": "   - 총 손상된 청크 수: {corrupted_count}",
        "ko_kr": "   - 총 손상된 청크 수: {corrupted_count}",
        "de_de": "   - Gesamt beschädigte Chunks: {corrupted_count}",
        "es_es": "   - Chunks corruptos totales: {corrupted_count}",
        "fr": "   - Chunks corrompus totaux: {corrupted_count}",
        "it_it": "   - Chunk corrotti totali: {corrupted_count}",
        "pt_br": "   - Chunks corrompidos totais: {corrupted_count}",
        "ru_ru": "   - Всего поврежденных чанков: {corrupted_count}",
        "tr": "   - Toplam hasarlı küme sayısı: {corrupted_count}",
        "da_dk": "   - Samlede beskadigede chunks: {corrupted_count}",
        "he_il": "   - סך הכל חלקים פגומים: {corrupted_count}",
        "hi_in": "   - कुल क्षतिग्रस्त चंक: {corrupted_count}",
        "th_th": "   - ชิ้นส่วนที่เสียหายทั้งหมด: {corrupted_count}",
        "ug_cn": "   - جەمئىي بۇزۇلغان بۆلەك سانى: {corrupted_count}",
        "uk_ua": "   - Всього пошкоджених чанків: {corrupted_count}",
        "vi_vn": "   - Tổng số khối bị hỏng: {corrupted_count}",
        "bo": "   - སྡེབ་གཅིག་གི་སྐྱོན་བཅོས་སྒྲིག་སྤར་བའི་སྐྱོན་བཅོས་སྒྲིག་སྤར་བའི།: {corrupted_count}",
    },
    "rs_recovery_started": {
        "ja_jp": "🔧 Reed-Solomon誤り訂正開始...",
        "ko_kp": "🔧 Reed-Solomon 오류 수정 시작...",
        "ko_kr": "🔧 Reed-Solomon 오류 수정 시작...",
        "de_de": "🔧 Reed-Solomon-Fehlerkorrektur wird gestartet...",
        "es_es": "🔧 Iniciando corrección de errores Reed-Solomon...",
        "fr": "🔧 Démarrage de la correction d'erreurs Reed-Solomon...",
        "it_it": "🔧 Avvio correzione errori Reed-Solomon...",
        "pt_br": "🔧 Iniciando correção de erros Reed-Solomon...",
        "ru_ru": "🔧 Запуск коррекции ошибок Reed-Solomon...",
        "tr": "🔧 Reed-Solomon hata düzeltme başlatılıyor...",
        "da_dk": "🔧 Starter Reed-Solomon fejlkorrektion...",
        "he_il": "🔧 מתחיל תיקון שגיאות Reed-Solomon...",
        "hi_in": "🔧 Reed-Solomon त्रुटि सुधार शुरू हो रहा है...",
        "th_th": "🔧 เริ่มการแก้ไขข้อผิดพลาด Reed-Solomon...",
        "ug_cn": "🔧 Reed-Solomon خاتالىق تۈزىتىش باشلىنىۋاتىدۇ...",
        "uk_ua": "🔧 Запускається корекція помилок Reed-Solomon...",
        "vi_vn": "🔧 Bắt đầu sửa lỗi Reed-Solomon...",
        "bo": "🔧 Reed-Solomon སྡེབ་གཅིག་གི་སྐྱོན་བཅོས་སྒྲིག་སྤར་བའི་སྐོར་ནས།...",
    },
    "rs_recovery_success": {
        "ja_jp": "   - {recovered_count}個の破損チャンクを正常に回復",
        "ko_kp": "   - {recovered_count}개의 손상된 청크를 성공적으로 복구",
        "ko_kr": "   - {recovered_count}개의 손상된 청크를 성공적으로 복구",
        "de_de": "   - {recovered_count} beschädigte Chunks erfolgreich wiederhergestellt",
        "es_es": "   - {recovered_count} chunks corruptos recuperados con éxito",
        "fr": "   - {recovered_count} chunks corrompus récupérés avec succès",
        "it_it": "   - {recovered_count} chunk corrotti recuperati con successo",
        "pt_br": "   - {recovered_count} chunks corrompidos recuperados com sucesso",
        "ru_ru": "   - Успешно восстановлено {recovered_count} поврежденных чанков",
        "tr": "   - {recovered_count} hasarlı küme başarıyla kurtarıldı",
        "da_dk": "   - {recovered_count} beskadigede chunks gendannet med succes",
        "he_il": "   - {recovered_count} חלקים פגומים שוחזרו בהצלחה",
        "hi_in": "   - {recovered_count} क्षतिग्रस्त चंक सफलतापूर्वक पुनर्प्राप्त किए गए",
        "th_th": "   - กู้คืนชิ้นส่วนที่เสียหาย {recovered_count} ชิ้นสำเร็จ",
        "ug_cn": "   - {recovered_count} بۇزۇلغان بۆلەك مۇۋەپپەقىيەتلىك ئەسلىگە كەلتۈرۈلدى",
        "uk_ua": "   - Успішно відновлено {recovered_count} пошкоджених чанків",
        "vi_vn": "   - Đã khôi phục thành công {recovered_count} khối bị hỏng",
        "bo": "   - {recovered_count} སྡེབ་གཅིག་གི་སྐྱོན་བཅོས་སྒྲིག་སྤར་བའི་སྐྱོན་བཅོས་སྒྲིག་སྤར་བའི་སྐོར་ནས་མངོན་པ།",
    },
    "rs_recovery_failed": {
        "ja_jp": "   - 訂正失敗: 訂正能力上限を超過 ({max_recoverable})",
        "ko_kp": "   - 수정 실패: 수정 한도 초과 ({max_recoverable})",
        "ko_kr": "   - 수정 실패: 수정 한도 초과 ({max_recoverable})",
        "de_de": "   - Korrektur fehlgeschlagen: Korrekturlimit überschritten ({max_recoverable})",
        "es_es": "   - Corrección fallida: excedido el límite de corrección ({max_recoverable})",
        "fr": "   - Correction échouée: limite de correction dépassée ({max_recoverable})",
        "it_it": "   - Correzione fallita: superato limite di correzione ({max_recoverable})",
        "pt_br": "   - Correção falhou: limite de correção excedido ({max_recoverable})",
        "ru_ru": "   - Коррекция не удалась: превышен предел коррекции ({max_recoverable})",
        "tr": "   - Düzeltme başarısız: düzeltme limiti aşıldı ({max_recoverable})",
        "da_dk": "   - Korrektion mislykkedes: korrektionsgrænse overskredet ({max_recoverable})",
        "he_il": "   - תיקון נכשל: חרג ממגבלת התיקון ({max_recoverable})",
        "hi_in": "   - सुधार विफल: सुधार सीमा पार ({max_recoverable})",
        "th_th": "   - การแก้ไขล้มเหลว: เกินขีดจำกัดการแก้ไข ({max_recoverable})",
        "ug_cn": "   - تۈزىتىش مەغلۇب بولدى: تۈزىتىش چېكى ئاشتى ({max_recoverable})",
        "uk_ua": "   - Корекція не вдалася: перевищено ліміт корекції ({max_recoverable})",
        "vi_vn": "   - Sửa lỗi thất bại: vượt quá giới hạn sửa lỗi ({max_recoverable})",
        "bo": "   - སྐྱོན་བཅོས་སྒྲིག་སྤར་བའི་སྐོར་ནས་མ་འགྲུབ་པ།: སྐྱོན་བཅོས་སྒྲིག་སྤར་བའི་ཚད་བརྒལ་བ། ({max_recoverable})",
    },
    "rs_verification_passed": {
        "ja_jp": "   - 修正後検証: ✓ 合格",
        "ko_kp": "   - 수정 후 검증: ✓ 통과",
        "ko_kr": "   - 수정 후 검증: ✓ 통과",
        "de_de": "   - Nachkorrektur-Verifizierung: ✓ Bestanden",
        "es_es": "   - Verificación posterior a la corrección: ✓ Aprobada",
        "fr": "   - Vérification post-correction: ✓ Réussie",
        "it_it": "   - Verifica post-correzione: ✓ Passata",
        "pt_br": "   - Verificação pós-correção: ✓ Aprovada",
        "ru_ru": "   - Проверка после коррекции: ✓ Прошла",
        "tr": "   - Düzeltme sonrası doğrulama: ✓ Başarılı",
        "da_dk": "   - Verifikation efter korrektion: ✓ Bestået",
        "he_il": "   - אימות לאחר תיקון: ✓ עברה",
        "hi_in": "   - सुधार के बाद सत्यापन: ✓ पास",
        "th_th": "   - การตรวจสอบหลังการแก้ไข: ✓ ผ่าน",
        "ug_cn": "   - تۈزىتىشتىن كېيىنكى دەلىللەش: ✓ ئۆتتى",
        "uk_ua": "   - Перевірка після корекції: ✓ Пройдена",
        "vi_vn": "   - Xác minh sau khi sửa lỗi: ✓ Đạt",
        "bo": "   - སྐྱོན་བཅོས་སྒྲིག་སྤར་བའི་སྐོར་ནས་མངོན་པ་: ✓ འགྲུབ་པ།",
    },
    "rs_verification_failed": {
        "ja_jp": "   - 修正後検証: ✗ 失敗 (ID: {chunk_ids})",
        "ko_kp": "   - 수정 후 검증: ✗ 실패 (ID: {chunk_ids})",
        "ko_kr": "   - 수정 후 검증: ✗ 실패 (ID: {chunk_ids})",
        "de_de": "   - Nachkorrektur-Verifizierung: ✗ Fehlgeschlagen (IDs: {chunk_ids})",
        "es_es": "   - Verificación posterior a la corrección: ✗ Fallida (IDs: {chunk_ids})",
        "fr": "   - Vérification post-correction: ✗ Échouée (IDs: {chunk_ids})",
        "it_it": "   - Verifica post-correzione: ✗ Fallita (ID: {chunk_ids})",
        "pt_br": "   - Verificação pós-correção: ✗ Falhou (IDs: {chunk_ids})",
        "ru_ru": "   - Проверка после коррекции: ✗ Неудачно (ID: {chunk_ids})",
        "tr": "   - Düzeltme sonrası doğrulama: ✗ Başarısız (kimlikler: {chunk_ids})",
        "da_dk": "   - Verifikation efter korrektion: ✗ Fejlet (ID'er: {chunk_ids})",
        "he_il": "   - אימות לאחר תיקון: ✗ נכשלה (מזהים: {chunk_ids})",
        "hi_in": "   - सुधार के बाद सत्यापन: ✗ विफल (आईडी: {chunk_ids})",
        "th_th": "   - การตรวจสอบหลังการแก้ไข: ✗ ล้มเหลว (ID: {chunk_ids})",
        "ug_cn": "   - تۈزىتىشتىن كېيىنكى دەلىللەش: ✗ مەغلۇب بولدى (ID: {chunk_ids})",
        "uk_ua": "   - Перевірка після корекції: ✗ Невдала (ID: {chunk_ids})",
        "vi_vn": "   - Xác minh sau khi sửa lỗi: ✗ Thất bại (ID: {chunk_ids})",
        "bo": "   - སྐྱོན་བཅོས་སྒྲིག་སྤར་བའི་སྐོར་ནས་མངོན་པ་: ✗ མ་འགྲུབ་པ། (ID: {chunk_ids})",
    },
    "corrupted_blocks_tip": {
        "ja_jp": "⚠ 回復不能: {unrecoverable_count}個の破損チャンク (ID: {chunk_ids})\n   ヒント: これらのQRコードを再スキャンしてください",
        "ko_kp": "⚠ 복구 불가: {unrecoverable_count}개의 손상된 청크 (ID: {chunk_ids})\n   팁: 이러한 QR 코드를 다시 스캔하세요",
        "ko_kr": "⚠ 복구 불가: {unrecoverable_count}개의 손상된 청크 (ID: {chunk_ids})\n   팁: 이러한 QR 코드를 다시 스캔하세요",
        "de_de": "⚠ Nicht wiederherstellbar: {unrecoverable_count} beschädigte Chunks (IDs: {chunk_ids})\n   Tipp: Bitte diese QR-Codes erneut scannen",
        "es_es": "⚠ Irrecuperable: {unrecoverable_count} chunks corruptos (IDs: {chunk_ids})\n   Consejo: Por favor, vuelva a escanear estos códigos QR",
        "fr": "⚠ Irrécupérable: {unrecoverable_count} chunks corrompus (IDs: {chunk_ids})\n   Conseil: Veuillez rescanner ces codes QR",
        "it_it": "⚠ Irrecuperabile: {unrecoverable_count} chunk corrotti (ID: {chunk_ids})\n   Suggerimento: Si prega di scansionare nuovamente questi codici QR",
        "pt_br": "⚠ Irrecuperável: {unrecoverable_count} chunks corrompidos (IDs: {chunk_ids})\n   Dica: Por favor, escaneie novamente esses códigos QR",
        "ru_ru": "⚠ Невосстанавливаемо: {unrecoverable_count} поврежденных чанков (ID: {chunk_ids})\n   Совет: Пожалуйста, просканируйте эти QR-коды снова",
        "tr": "⚠ Kurtarılamaz: {unrecoverable_count} hasarlı küme (kimlikler: {chunk_ids})\n   İpucu: Lütfen bu QR kodlarını tekrar taratın",
        "da_dk": "⚠ Ugendannelig: {unrecoverable_count} beskadigede chunks (ID'er: {chunk_ids})\n   Tip: Scan venligst disse QR-koder igen",
        "he_il": "⚠ בלתי ניתן לשחזור: {unrecoverable_count} חלקים פגומים (מזהים: {chunk_ids})\n   טיפ: אנא סרוק שוב קודי QR אלו",
        "hi_in": "⚠ अपुनर्प्राप्य: {unrecoverable_count} क्षतिग्रस्त चंक (आईडी: {chunk_ids})\n   सुझाव: कृपया इन QR कोड को फिर से स्कैन करें",
        "th_th": "⚠ ไม่สามารถกู้คืนได้: {unrecoverable_count} ชิ้นส่วนที่เสียหาย (ID: {chunk_ids})\n   เคล็ดลับ: โปรดสแกนคิวอาร์โค้ดเหล่านี้อีกครั้ง",
        "ug_cn": "⚠ ئەسلىگە كەلتۈرگىلى بولمايدۇ: {unrecoverable_count} بۇزۇلغان بۆلەك (ID: {chunk_ids})\n   تەكلىپ: بۇ QR كودلىرىنى قايتا تەكشۈرۈڭ",
        "uk_ua": "⚠ Не відновлюється: {unrecoverable_count} пошкоджених чанків (ID: {chunk_ids})\n   Порада: Будь ласка, повторно відскануйте ці QR-коди",
        "vi_vn": "⚠ Không thể khôi phục: {unrecoverable_count} khối bị hỏng (ID: {chunk_ids})\n   Gợi ý: Vui lòng quét lại các mã QR này",
        "bo": "⚠ སླར་གསོ་བྱེད་ཐབས་བྲལ་བ།: {unrecoverable_count} སྡེབ་གཅིག་གི་སྐྱོན་བཅོས་སྒྲིག་སྤར་བའི་སྐྱོན་བཅོས་སྒྲིག་སྤར་བའི་སྐོར་ནས་མངོན་པ། (ID: {chunk_ids})\n   གླེང་གཞི།: སྐུ་མགྲོན་ལགས་ཀྱིས་QR སྐད་འཕྲིན་འདི་དག་བསྐྱར་ཞིབ་བྱོན་རོགས།",
    },
    "redundancy_not_enabled": {
        "ja_jp": "   - 冗長性訂正: 有効ではありません",
        "ko_kp": "   - 중복성 수정: 사용 안 함",
        "ko_kr": "   - 중복성 수정: 사용 안 함",
        "de_de": "   - Redundanzkorrektur: Nicht aktiviert",
        "es_es": "   - Corrección de redundancia: No activada",
        "fr": "   - Correction de redondance: Non activée",
        "it_it": "   - Correzione ridondanza: Non abilitata",
        "pt_br": "   - Correção de redundância: Não ativada",
        "ru_ru": "   - Коррекция избыточности: Не включено",
        "tr": "   - Artıklık düzeltme: Etkin değil",
        "da_dk": "   - Redundanskorrektion: Ikke aktiveret",
        "he_il": "   - תיקון יתירות: לא מופעל",
        "hi_in": "   - प्रतिकृति सुधार: सक्षम नहीं",
        "th_th": "   - การแก้ไขความซ้ำซ้อน: ไม่ได้เปิดใช้งาน",
        "ug_cn": "   - ئارتۇقچە تۈزىتىش: قوزغىتىلمىغان",
        "uk_ua": "   - Корекція надлишковості: Не увімкнено",
        "vi_vn": "   - Sửa lỗi dư thừa: Không được bật",
        "bo": "   - སྡེབ་གཅིག་གི་སྐྱོན་བཅོས་སྒྲིག་སྤར་བའི་སྐོར་ནས་མངོན་པ།: སྤར་བའི།",
    },
    "verification_summary": {
        "ja_jp": "   - 検証結果: {valid_count}個正常, {corrupted_count}個破損",
        "ko_kp": "   - 검증 결과: {valid_count}개 정상, {corrupted_count}개 손상됨",
        "ko_kr": "   - 검증 결과: {valid_count}개 정상, {corrupted_count}개 손상됨",
        "de_de": "   - Überprüfungsergebnisse: {valid_count} gültig, {corrupted_count} beschädigt",
        "es_es": "   - Resultados de verificación: {valid_count} válidos, {corrupted_count} corruptos",
        "fr": "   - Résultats de vérification: {valid_count} valides, {corrupted_count} corrompus",
        "it_it": "   - Risultati verifica: {valid_count} validi, {corrupted_count} corrotti",
        "pt_br": "   - Resultados de verificação: {valid_count} válidos, {corrupted_count} corrompidos",
        "ru_ru": "   - Результаты проверки: {valid_count} допустимо, {corrupted_count} повреждено",
        "tr": "   - Doğrulama sonuçları: {valid_count} geçerli, {corrupted_count} hasarlı",
        "da_dk": "   - Verifikationsresultater: {valid_count} gyldige, {corrupted_count} beskadigede",
        "he_il": "   - תוצאות אימות: {valid_count} תקינים, {corrupted_count} פגומים",
        "hi_in": "   - सत्यापन परिणाम: {valid_count} मान्य, {corrupted_count} क्षतिग्रस्त",
        "th_th": "   - ผลการตรวจสอบ: {valid_count} ถูกต้อง, {corrupted_count} เสียหาย",
        "ug_cn": "   - دەلىللەش نەتىجىسى: {valid_count} نورمال, {corrupted_count} بۇزۇلغان",
        "uk_ua": "   - Результати перевірки: {valid_count} дійсних, {corrupted_count} пошкоджених",
        "vi_vn": "   - Kết quả xác minh: {valid_count} hợp lệ, {corrupted_count} bị hỏng",
        "bo": "   - ཞིབ་བཤེར་གྱི་འབྲས་བུ།: {valid_count} སྐྱོན་མེད་པ།, {corrupted_count} སྡེབ་གཅིག་གི་སྐྱོན་བཅོས་སྒྲིག་སྤར་བའི་སྐོར་ནས་མངོན་པ།",
    },
}

def update_language_file(lang_code):
    """更新单个语言文件"""
    file_path = os.path.join(LOCALES_DIR, f"{lang_code}.json")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"⚠️  File not found: {file_path}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error in {file_path}: {e}")
        return False
    
    updated = False
    
    # 更新GUI翻译
    if 'gui' not in data:
        data['gui'] = {}
    
    for key, translations in GUI_TRANSLATIONS.items():
        if key not in data['gui']:
            if lang_code in translations:
                data['gui'][key] = translations[lang_code]
                updated = True
    
    # 更新auto_split_qr翻译
    if 'auto_split_qr' not in data:
        data['auto_split_qr'] = {}
    
    for key, translations in AUTO_SPLIT_QR_TRANSLATIONS.items():
        if key not in data['auto_split_qr']:
            if lang_code in translations:
                data['auto_split_qr'][key] = translations[lang_code]
                updated = True
    
    # 更新scanner_decoder翻译
    if 'scanner_decoder' not in data:
        data['scanner_decoder'] = {}
    
    for key, translations in SCANNER_DECODER_TRANSLATIONS.items():
        if key not in data['scanner_decoder']:
            if lang_code in translations:
                data['scanner_decoder'][key] = translations[lang_code]
                updated = True
    
    if updated:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✅ Updated: {lang_code}.json")
            return True
        except Exception as e:
            print(f"❌ Error writing {file_path}: {e}")
            return False
    else:
        print(f"⏭️  No updates needed: {lang_code}.json")
        return True

def main():
    """主函数"""
    # 需要更新的语言代码（排除已经手动更新的zh_cn和en_us）
    languages = [
        "ja_jp", "ko_kp", "ko_kr", "de_de", "es_es", "fr", "it_it", 
        "pt_br", "ru_ru", "tr", "da_dk", "he_il", "hi_in", "th_th", 
        "ug_cn", "uk_ua", "vi_vn", "bo"
    ]
    
    print("🔄 开始更新语言文件...")
    success_count = 0
    
    for lang_code in languages:
        if update_language_file(lang_code):
            success_count += 1
    
    print(f"\n✅ 完成！成功更新 {success_count}/{len(languages)} 个语言文件")

if __name__ == "__main__":
    main()