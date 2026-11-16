---
name: watch
description: Check the official exam pages and the course page for new Greek exam dates, registration windows and course intakes, and put the next dates on the app's home screen. Use when the learner asks "any exam dates?", "when can I register?", "has the course opened?", "sınav tarihleri belli mi?", "kayıt ne zaman?", when a check-in finds the last check older than 7 days, or when it runs on a weekly schedule.
---

# Watch: exam dates and courses

Exam sessions are announced late and places can be capped. Missing a registration window costs half a year. This skill checks the official pages and keeps `coach/watch.json` current. The home screen shows the next date from it.

**First read `docs/COACHING.md` §1 and §7.** If you have no web access in this harness, say so in one line and stop. Never fill in dates from memory.

## Steps

1. Collect the sources:
   - each exam blueprint `exams/<id>.json` has a `watch` block (`what`, `urls`, `look_for`), for the exam with that id;
   - `exams/watch-sources.json` holds the rest (the course page), each with `kind`, `urls` and `look_for`.

   `look_for` says what counts as news.
2. Read the current `<learner_dir>/coach/watch.json` if there is one. It is the previous state.
3. **Fetch every URL** with your web tool and look for what `look_for` describes:
   - exam dates;
   - registration opening and closing dates;
   - for the course, intakes whose class hours fit the learner (the condition is in `look_for` and in `profile.course`).

   Follow a link to an announcement page if the date is there and not on the main page. Stay on the official site.
   - **University of Athens courses:** the class hours and registration dates are only in the PDF schedule of each course, linked from the programme page. If your web tool cannot read a PDF, read the copy it saved.
   - **An exam that runs every year but has no announced date yet** (B1 in October): write an entry with `"date": null` and a `note` saying when it was last held, so the plan can name it as a possibility.
4. **Only write what you saw.**
   - A date goes in only if the page says it.
   - If a page could not be reached, keep that source's previous entries unchanged and add `"note": "could not check on <date>"`.
   - If something is ambiguous (a year missing, two dates), write what is certain and put the doubt in `note`.
5. **Write `<learner_dir>/coach/watch.json`:**

   ```json
   {"checked_at": "2026-11-16T10:00:00+02:00",
    "entries": [
      {"what": "Ελληνομάθεια B1, May 2027", "what_tr": "Ελληνομάθεια B1, Mayıs 2027", "kind": "exam", "exam": "b1-keg",
       "date": "2027-05-13", "registration": {"opens": "2027-02-01", "closes": "2027-03-14"},
       "source_url": "https://www.greek-language.gr/certification/node/15.html", "changed": false},
      {"what": "UoA evening course, spring intake", "kind": "course", "date": null,
       "registration": null, "source_url": "https://en.greekcourses.uoa.gr/program_of_courses",
       "changed": false, "note": "no course after 17:00 announced yet"}
    ]}
   ```

   - Dates are `YYYY-MM-DD`.
   - For an exam entry, set `"exam"` to the blueprint id (`"b1-keg"` or `"a2ltr"`). The plan uses it to match the date to the exam.
   - An exam with no announced session still gets an entry with `"date": null` and a `note` ("no 2027 call yet"). The plan then says plainly that there is no date.
   - `what` is English and short; `what_tr` is the Turkish.
   - Set `changed: true` for an entry that is new, or whose date or registration differs from the previous file.
   - Keep past entries out once their dates have passed. Leave out a course whose registration has closed, and mention it in `coach/notes.md` instead.
6. Run `uv run greek-coach validate <learner_dir>`, then `uv run greek-coach reload`.

## Telling the learner

- If anything has `changed: true`, tell them in one or two plain lines in their language, with what to do and by when: "Registration for the May B1 exam opens on 1 February and closes on 14 March."
- If nothing changed, say "no new dates" in one line, or say nothing if this ran inside a check-in.
- Never tell them to book. That is their decision, and the residence-permit question is for their lawyer (SPEC §1.1). You can say which session their numbers make realistic: the `plan` skill does that, from these dates.

## On a schedule

A weekly run is set up like daily prep's (see `.agents/skills/daily-prep/SKILL.md`, "Setting up the schedule"), with:

```
uv run greek-coach schedule add watch --every week --day MON --at HH:MM
```

In a scheduled run (`GREEK_COACH_SCHEDULED_RUN` is set), never ask anything. Write the file and finish with a one-line summary.
