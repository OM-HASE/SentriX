import ollama


def detect_language(source_code):

    code = source_code.lower().strip()

    # =========================
    # FAST LIGHTWEIGHT DETECTION
    # =========================

    # Python
    python_keywords = [
        "def ",
        "import ",
        "print(",
        "self",
        "__name__",
        "from ",
        "elif ",
        "except"
    ]

    # JavaScript
    javascript_keywords = [
        "console.log",
        "function ",
        "=>",
        "let ",
        "const ",
        "var ",
        "document.getelementbyid",
        "window."
    ]

    # TypeScript
    typescript_keywords = [
        "interface ",
        ": string",
        ": number",
        "implements ",
        "readonly "
    ]

    # Java
    java_keywords = [
        "public class",
        "public static void main",
        "system.out.println",
        "private ",
        "protected ",
        "extends "
    ]

    # C
    c_keywords = [
        "#include<stdio.h>",
        "printf(",
        "scanf(",
        "malloc(",
        "free("
    ]

    # C++
    cpp_keywords = [
        "#include<iostream>",
        "std::cout",
        "std::cin",
        "using namespace std",
        "class "
    ]

    # Go
    go_keywords = [
        "package main",
        "fmt.println",
        "func main",
        "go func",
        "defer "
    ]

    # Rust
    rust_keywords = [
        "fn main",
        "println!",
        "let mut",
        "impl ",
        "trait "
    ]

    # C#
    csharp_keywords = [
        "using system",
        "using system.collections",
        "namespace ",
        "public class ",
        "static void main",
        "console.writeline",
        "console.readline",
        "string[] args",
        "list<",
        "dictionary<",
        "var ",
        "async task",
        "await ",
        "?.","??",
    ]

        # HTML
    html_keywords = [
        "<html",
        "<body",
        "<div",
        "<head",
        "<script",
        "<!doctype html"
    ]

    # CSS
    css_keywords = [
        "{",
        "color:",
        "margin:",
        "padding:",
        "display:",
        "font-size:",
        "background:"
    ]

    # PHP
    php_keywords = [
        "<?php",
        "echo ",
        "$_post",
        "$_get",
        "->"
    ]

    # SQL
    sql_keywords = [
        "select ",
        "insert into",
        "update ",
        "delete from",
        "create table"
    ]

    # Swift
    swift_keywords = [
        "import swift",
        "let ",
        "var ",
        "func ",
        "swiftui"
    ]

    # Kotlin
    kotlin_keywords = [
        "fun main",
        "val ",
        "var ",
        "println(",
        "class "
    ]

    # =========================
    # FAST DETECTION CHECKS
    # =========================

    language_patterns = {

        "Python": python_keywords,

        "JavaScript": javascript_keywords,

        "TypeScript": typescript_keywords,

        "Java": java_keywords,

        "C": c_keywords,

        "C++": cpp_keywords,

        "Go": go_keywords,

        "Rust": rust_keywords,

        "HTML": html_keywords,

        "CSS": css_keywords,

        "PHP": php_keywords,

        "SQL": sql_keywords,

        "Swift": swift_keywords,

        "Kotlin": kotlin_keywords,
        "C#": csharp_keywords
    }

    for language, keywords in language_patterns.items():

        for keyword in keywords:

            if keyword in code:

                return language

    # =========================
    # LLM FALLBACK
    # =========================

    prompt = f"""
You are an expert programming language detector.

Identify the programming language of the following code.

Return ONLY the language name.

CODE:
{source_code}
"""

    response = ollama.chat(

        model="qwen2.5-coder:7b",

        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],

        stream=False,

        options={
            "num_predict": 20
        }
    )

    language = response[
        "message"
    ]["content"].strip()

    return language