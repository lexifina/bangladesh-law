# Sources

| Source | What it gives | Used |
| --- | --- | --- |
| [Laws of Bangladesh](http://bdlaws.minlaw.gov.bd) (Legislative and Parliamentary Affairs Division) | Every law in its chronological index, in force or repealed, each with its current text and amendment footnotes, in English or Bengali | Yes: the text of every law here |
| `GET /laws-of-bangladesh-chronological-index.html` | The whole index on one page: each law's site id, title (marked `[Repealed]` where repealed), number and year | Yes: the list of laws |
| `GET /act-<id>.html` | A law's table of contents (section numbers and names) and a link to its text in the other language, where there is one | Yes: section names, language links |
| `GET /act-details-<id>.html` | A law's whole text: title, number line, date, preamble, Part and Chapter headings, each section, and the footnotes | Yes: the text |
| Bangladesh Gazette | The authentic text | No: not published as a consolidated, searchable whole |

Retrieved {{RETRIEVED}}: {{INDEX}} laws in the index, read from the index and two pages per law. One law, the Lunacy Act, 1912 (site id 96, repealed), could not be read: both its pages were server errors. The sha256 of every page the build read is in [`data/source-sha256.tsv`](data/source-sha256.tsv).

## Terms and history

- **Terms**: the site has no terms of use. Its footer reads "Copyright © 2019, Legislative and Parliamentary Affairs Division Ministry of Law, Justice and Parliamentary Affairs". Nothing on the site forbids reuse, and nothing grants a licence.
- **History**: none. Each law has one text, the current one, with no date of its own. Hence `history: "current-only"`.

## Legal basis for reuse

**No exclusion was found.** No provision of Bangladesh law was found that takes Acts or other official texts out of copyright, or that allows them to be reproduced. This was checked in the Copyright Act, 2023 (Act No. 34 of 2023, site id 1452, in Bengali only), which repealed the Copyright Act, 2000. It was also checked by searching the text of every law in force on the site for provisions on copyright. The Copyright Act, 2000 is shown on the site as repealed, with no text, so its list of acts that were not infringements could not be read there.

What the Copyright Act, 2023 says, quoted from the site's text. The English renderings are Lexifina's working translations, not official ones. Section 128 lets the Government publish an authentic English text, and none was found on the site.

- Section 2(49) defines a Government work ("সরকারি কর্ম") to include works made under the direction or control of the law-making authority:

  > (৪৯) “সরকারি কর্ম” অর্থ নিম্নবর্ণিত কোনো কর্তৃপক্ষ দ্বারা বা উহাদের অধীনে প্রদত্ত কোনো আদেশ, নির্দেশ বা নিয়ন্ত্রণে সম্পাদিত বা জারীকৃত কর্ম -
  > (ক) সরকার বা সরকারের কোনো বিভাগ, সংস্থা বা প্রতিষ্ঠান অথবা স্থানীয় কর্তৃপক্ষ বা সংবিধিবদ্ধ সরকারি কর্তৃপক্ষ;
  > (খ) বাংলাদেশের আইন প্রণয়নকারী কর্তৃপক্ষ; এবং
  > (গ) বাংলাদেশের কোনো আদালত, ট্রাইব্যুনাল বা বিচার বিভাগীয় অন্য কোনো কর্তৃপক্ষ।

  ("'Government work' means a work made or issued by, or under any order, direction or control given by, any of these authorities: (a) the Government, or any department, agency or institution of the Government, or a local authority or statutory public authority; (b) the law-making authority of Bangladesh; and (c) any court, tribunal or other judicial authority of Bangladesh.")
- Section 15(ঙ) makes the Government the first owner: "(ঙ) ভিন্নতর কোনো চুক্তি না থাকিলে, কোনো সরকারি কর্মের ক্ষেত্রে, সরকার উক্ত কর্মের কপিরাইটের প্রথম স্বত্বাধিকারী হইবেন;" ("in the case of a Government work, unless there is an agreement to the contrary, the Government shall be the first owner of its copyright").
- Section 28 sets the term: "২৮। কোনো সরকারি কর্মের কপিরাইটের ক্ষেত্রে, যে বৎসর কর্মটি প্রথম প্রকাশিত হইয়াছে তাহার পরবর্তী ৬০ (ষাট) বৎসর পর্যন্ত কপিরাইট বিদ্যমান থাকিবে।" ("In the case of a Government work, copyright subsists for 60 (sixty) years after the year in which the work was first published.")
- Section 70(1), on acts that are not infringements, leaves the purposes and conditions to rules: "৭০। (১) এতদুদ্দেশ্যে বিধিতে উল্লিখিত উদ্দেশ্য ও শর্ত অনুসারে যদি কোনো সাহিত্য, নাট্য, সংগীত বা শিল্পকর্মের পুনরুৎপাদন, অভিযোজন, শব্দ-ধ্বনি রেকর্ডিং প্রচার, সম্প্রচার, প্রদর্শন, প্রকাশন বা সদ্ব্যবহার করা হয় কিংবা অন্য যে কোনো ভাষায় অনুবাদ তৈরি বা প্রকাশনা করা হয় তাহা হইলে উক্তরূপ কার্যাদি দ্বারা কপিরাইট লঙ্ঘিত হইবে না।" ("If a literary, dramatic, musical or artistic work is reproduced, adapted, ... published or fairly used, or translated into any other language, in accordance with the purposes and conditions set out in the rules for this purpose, copyright is not infringed by those acts.") The rules are not on the site and were not found. Section 70(2) covers formats for blind people only.
- Section 127(2)(ক) keeps rules made under the Copyright Act, 2000 in force, so far as they are consistent with the 2023 Act, until repealed or amended. Any rules on reproducing official texts under the 2000 Act were not found either.

So, on what was found, the text of an Act of Parliament is a Government work under the Copyright Act, 2023. The Government owns its copyright for 60 years after the year it was first published, and reproducing it is lawful only as rules under section 70 allow. Older laws (published before 1966) may be out of that term, but their current texts carry amendments and footnotes written later, and the site's consolidation and footnotes are the Division's own work.

**So this repository is private.** Before it is made public, the rules under section 70 (or under the 2000 Act, kept by section 127) should be found and read, or the Legislative and Parliamentary Affairs Division asked for permission.
