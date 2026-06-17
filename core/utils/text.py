def split_sentences(txt: str) -> list[str]:
    """
    Python equivalent of the TypeScript splitSentences algorithm.
    Splits text by punctuation or paragraph breaks while respecting quote blocks
    and preserving trailing whitespaces and newlines.
    """
    if not txt:
        return []
    sentences = []
    current = ""
    in_quotes = False
    quote_char = ""
    punct_terminators = {'.', '!', '?', '。', '！', '？'}
    newlines = {'\n', '\r'}
    
    txt_len = len(txt)
    i = 0
    while i < txt_len:
        char = txt[i]
        current += char
        
        if char in ('"', '“', '”', '「', '」', '『', '』'):
            if not in_quotes and char in ('"', '“', '「', '『'):
                in_quotes = True
                quote_char = char
            elif in_quotes:
                if (
                    (quote_char == '「' and char == '」') or
                    (quote_char == '『' and char == '』') or
                    (quote_char == '“' and char == '”') or
                    (quote_char == '"' and char == '"')
                ):
                    in_quotes = False
                    quote_char = ""
                    
                    has_terminator_before = len(current) > 1 and (
                        current[-2] in punct_terminators or current[-2] in newlines
                    )
                    
                    next_char_idx = i + 1
                    while next_char_idx < txt_len and txt[next_char_idx] == ' ':
                        next_char_idx += 1
                    next_char = txt[next_char_idx] if next_char_idx < txt_len else ''
                    
                    next_is_uppercase = (
                        len(next_char) == 1 and
                        next_char.isupper() and
                        next_char.lower() != next_char
                    )
                    next_is_newline = next_char in newlines
                    next_is_bracket = next_char in ('「', '『', '”', '"', '“')
                    
                    if has_terminator_before or next_is_uppercase or next_is_newline or next_is_bracket:
                        next_is_term = (
                            i + 1 < txt_len and
                            (txt[i + 1] in punct_terminators or txt[i + 1] in newlines)
                        )
                        if not next_is_term:
                            peek = i + 1
                            while peek < txt_len and txt[peek] in (' ', '\n', '\r'):
                                current += txt[peek]
                                peek += 1
                            if current.strip():
                                sentences.append(current)
                            current = ""
                            i = peek - 1
        elif not in_quotes:
            if char in punct_terminators:
                next_is_punct = i + 1 < txt_len and txt[i+1] in punct_terminators
                next_is_quote = i + 1 < txt_len and txt[i+1] in ('」', '』', '”', '"')
                if next_is_punct or next_is_quote:
                    i += 1
                    continue
                
                peek = i + 1
                while peek < txt_len and txt[peek] in (' ', '\n', '\r'):
                    current += txt[peek]
                    peek += 1
                if current.strip():
                    sentences.append(current)
                current = ""
                i = peek - 1
            elif char in newlines:
                next_is_newline = i + 1 < txt_len and txt[i+1] in newlines
                if next_is_newline:
                    i += 1
                    continue
                
                peek = i + 1
                while peek < txt_len and txt[peek] in (' ', '\n', '\r'):
                    current += txt[peek]
                    peek += 1
                if current.strip():
                    sentences.append(current)
                current = ""
                i = peek - 1
        i += 1
        
    if current.strip():
        sentences.append(current)
    return [s for s in sentences if s.strip()]
