GREETING_TEMPLATE = """
[Indonesian]
Halo! Saya Aiwa, asisten AI dari Warna Warni Media, siap membantu Anda ☺️
------
[English]
Hello! I am Aiwa, the AI assistant from Warna Warni Media, ready to assist you ☺️
"""

FACTUAL_FALLBACK_TEMPLATE = """
[Indonesian]
Maaf, saya tidak memiliki informasi mengenai hal tersebut.
------
[English]
Sorry, I do not have information about that.
"""

CREATE_MEETING_TEMPLATE = """
[Indonesian]
Berikut detail yang kami butuhkan untuk menjadwalkan meeting:

- 💻 Judul Meeting: 
- 🗓️ Tanggal & Waktu (contoh: 2025-09-18, 09:00 – 10:00 WIB): 
- 👥 Email Peserta (kosongkan jika tidak ada undangan email): 

Silakan lengkapi data yang masih kosong di atas. 🚀
------
[English]
Here are the details we need to schedule your meeting:

- 💻 Meeting Title: 
- 🗓️ Date & Time (e.g., 2025-09-18, 09:00 – 10:00 WIB): 
- 👥 Participant Email (leave empty if no email invitation): 

Please fill in the missing fields above. 🚀
"""

CONFIRM_MEETING_TEMPLATE = """
[Indonesian]
Apakah jadwal ini sudah benar tanpa perubahan?

- 💻 Judul Meeting: {{summary}}
- 🗓️ Tanggal & Waktu: {{date}}, {{start_time}} – {{end_time}} WIB
- 👥 Peserta: {{email}}

Balas "Ya" untuk membuat acara di Google Calendar
------
[English]
Is this schedule correct with no changes?

- 💻 Meeting Title: {{summary}}
- 🗓️ Date & Time: {{date}}, {{start_time}} – {{end_time}} WIB
- 👥 Attendee(s): {{email}}

Reply "Yes" to create the event in Google Calendar
"""

POST_CREATION_TEMPLATE = """
[Indonesian]
✅ Meeting berhasil dibuat:

- 💻 Judul Meeting: {{summary}}
- 🆔 Meeting ID: {{event_id}}
- 🗓️ Tanggal & Waktu: {{date}}, {{start_time}} – {{end_time}} WIB
- 👥 Peserta: {{email}}
- 🔗 Link Google Meet: {{meet_link}}
- 📌 Link Kalender: {{calendar_link}}

Silakan konfirmasi jika ada perubahan atau tambahan. Selamat meeting!
------
[English]
✅ Meeting has been created:

- 💻 Meeting Title: {{summary}}
- 🆔 Meeting ID: {{event_id}}
- 🗓️ Date & Time: {{date}}, {{start_time}} – {{end_time}} WIB
- 👥 Attendee(s): {{email}}
- 🔗 Google Meet Link: {{meet_link}}
- 📌 Calendar Link: {{calendar_link}}

Please confirm if there are any changes or additions. Have a great meeting!
"""

DELETE_REQUEST_ID_TEMPLATE = """
[Indonesian]
Untuk menghapus meeting, kami membutuhkan Meeting ID. 
Silakan kirim chat: *DELETE : [Meeting ID]*
------
[English]
To delete a meeting, we need the Meeting ID.
Please send a chat: *DELETE : [Meeting ID]*
"""

POST_DELETION_TEMPLATE = """
[Indonesian]
✅ Meeting telah berhasil dihapus:

- 💻 Judul Meeting: {{summary}}
- 🆔 Meeting ID: {{event_id}}
- 🗓️ Tanggal & Waktu: {{date}}, {{start_time}} – {{end_time}} WIB
- 👥 Peserta: {{attendees}}

Jika Anda membutuhkan bantuan lebih lanjut, jangan ragu untuk memberi tahu saya.
------
[English]
✅ Meeting has been successfully deleted:

- 💻 Meeting Title: {{summary}}
- 🆔 Meeting ID: {{event_id}}
- 🗓️ Date & Time: {{date}}, {{start_time}} – {{end_time}} WIB
- 👥 Attendees: {{attendees}}

If you need any further assistance, feel free to let me know.
"""
