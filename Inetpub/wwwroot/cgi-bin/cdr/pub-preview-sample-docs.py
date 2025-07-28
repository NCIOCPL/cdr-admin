#!/usr/bin/env python

"""Show menu for testing publish preview on representative PDQ summaries.
"""

from cdrcgi import Controller


class Control(Controller):
    """Processing control for new publish preview prototype."""

    SUBTITLE = "Sample Summary Publish Preview Reports"
    PP = "PublishPreview.py"
    CIS = {
        # Summary Type:
        "Adult Treatment": {
            # Topic: [HP English, Spanish], [Patient English, Spanish]
            "Breast": [[62787, 256668], [62955, 256762]],
            "Gastric": [[62911, 256670], [271446, 256764]],
            "Merkel Cell": [[62884, 256759], [441548, 470863]],
        },
        "Ped Treatment": {
            "Brain Stem Glioma": [[62761, 256675], [62962, 600419]],
            "Retinoblastoma": [[62846, 256693], [258033, 448617]],
        },
        "Genetics": {
            "Breast and Gynecologic": [[62855, None]],
            "Prostate": [[299612, None]],
        },
        "Integrative, alternative, and complementary therapies": {
            "High-Dose Vitamin C": [[742114, 773659], [742253, 773656]],
            "Mistletoe Extracts": [[269596, 778124], [449678, 778123]],
            "Bovine Shark Cartilage": [[62974, 789591], [446198, 789592]],
        },
        "Prevention": {
            "Breast": [[62779, 744468], [257994, 744469]],
            "Lung": [[62824, 733624], [62825, 729199]],
        },
        "Screening": {
            "Breast": [[62751, 744470], [257995, 744471]],
            "Lung": [[62832, 700433], [258019, 700560]],
        },
        "Supportive": {
            "Fatigue": [[62734, 256627], [62811, 256650]],
            "Pruritus": [[62748, 256645], [62805, 256622]],
        },
    }
    DIS = {
        "Bevacizumab": 487564,
        "BEP": 682526,
        "Blinatumomab": 767077,
    }

    def populate_form(self, page):
        """Provide the links to the sample summary publish preview reports.

        Pass:
            page - HTMLPage object where the links are put
        """

        fieldset = page.fieldset("Drugs")
        ul = page.B.UL()
        for title in sorted(self.DIS):
            url = self.make_url(self.PP, DocId=self.DIS[title])
            opts = dict(href=url, target="_blank")
            ul.append(page.B.LI(page.B.A(f"{title} Drug Summary", **opts)))
        fieldset.append(ul)
        page.form.append(fieldset)
        for summary_type in sorted(self.CIS):
            topics = self.CIS[summary_type]
            fieldset = page.fieldset(summary_type)
            ul = page.B.UL()
            for topic in sorted(topics):
                audience = "HP"
                for doc_ids in topics[topic]:
                    language = "English"
                    for doc_id in doc_ids:
                        if doc_id is not None:
                            title = f"{audience} {topic} Summary ({language})"
                            url = self.make_url(self.PP, DocId=doc_id)
                            opts = dict(href=url, target="_blank")
                            ul.append(page.B.LI(page.B.A(title, **opts)))
                        language = "Spanish"
                    audience = "Patient"
            fieldset.append(ul)
            page.form.append(fieldset)
        page.body.set("class", "admin-menu")
        page.add_css(".admin-menu li { font-weight: normal }")


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
