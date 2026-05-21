import re


# =========================================
# GENERATE REPAIR PLANS
# =========================================

def generate_repair_plan(

    error_log,

    source_code
):

    repairs = []

    # =====================================
    # runserver FIX
    # =====================================

    if "runserver" in source_code:

        repairs.append({

            "issue":
            "Invalid Flask API",

            "fix":
            "Replace app.runserver() with app.run()",

            "confidence":
            0.99,

            "risk":
            "Low"
        })

    # =====================================
    # addd FIX
    # =====================================

    if ".addd(" in source_code:

        repairs.append({

            "issue":
            "Invalid List API",

            "fix":
            "Replace addd() with add()",

            "confidence":
            0.98,

            "risk":
            "Low"
        })

    # =====================================
    # DIVISION BY ZERO
    # =====================================

    if "/ 0" in source_code:

        repairs.append({

            "issue":
            "Division by Zero",

            "fix":
            "Validate denominator before division",

            "confidence":
            0.95,

            "risk":
            "Medium"
        })

    # =====================================
    # NULL POINTER
    # =====================================

    if "null" in source_code.lower():

        repairs.append({

            "issue":
            "Potential Null Dereference",

            "fix":
            "Add null validation before access",

            "confidence":
            0.90,

            "risk":
            "Medium"
        })

    return repairs