import os
from fastapi import FastAPI, Body, Request, HTTPException
from keybert import KeyBERT
from kiwipiepy import Kiwi
from reranker import KoreanTechReranker

# from konlpy.tag import Okt
import uvicorn
# KEYBERT_MODEL_NAME = os.getenv("KEYBERT_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
KEYBERT_MODEL_NAME = os.getenv("KEYBERT_MODEL", "snunlp/KR-SBERT-V40K-klueNLI-augSTS")
CROSS_ENCODER_MODEL_NAME = os.getenv("CROSS_ENCODER_MODEL", "HJUNN/klue-roberta-small-cross-encoder")

app = FastAPI()
KIWI = Kiwi()

KEYBERT = KeyBERT(KEYBERT_MODEL_NAME)
RERANKER = KoreanTechReranker(CROSS_ENCODER_MODEL_NAME)


@app.post("/api/engine/tokenize")
async def tokenize(
    text: str = Body(..., embed=True)
):
    tokens = [{
        "id": t.id,
        "form": t.form,
        "tag": t.tag,
        "start": t.start,
        "end": t.end,
        "tagged_form": t.tagged_form,
        "word_position": t.word_position,
        "lemma": t.lemma,
        "score": t.score
    }
            for t in KIWI.tokenize(text, split_sents=False) ]
    return tokens

@app.post("/api/engine/extract-keywords")
async def extract(
        text: str = Body(..., embed=True), 
        top_n: int=5,
        diversity: float=0.7,
        use_mmr: bool=True,
        ngram_start: int=1,
        ngram_end: int=1,
        tokenize: bool=False,
        stop_words: str=''
    ):
    tokens = text
    if tokenize:
        tokens = " ".join(
            [t.form  # type: ignore 
             for t in KIWI.tokenize(text, split_sents=False) 
             if t.tag.startswith('N')] # type: ignore
        )  
    _stopwords = 'english'
    if stop_words:
        _stopwords = stop_words.split(',')
    keywords = KEYBERT.extract_keywords(
        tokens,
        keyphrase_ngram_range=(ngram_start, ngram_end),
        top_n=top_n,
        stop_words=_stopwords,
        use_mmr=use_mmr,          # 중복 방지
        diversity=diversity          # 다양성 조절
    )
    return {"keywords": [kw[0] for kw in keywords]}

@app.post("/api/engine/rerank")
async def rerank_endpoint(
        request: Request,
        top_k: int = 5
    ):
    """크로스 인코더 기반 Rerank 엔드포인트

    body:  
    ```json
    {
        "pr_data": {},
        "candidate_nodes": []
    }
    ```

    Args:
        top_k (int, optional): _description_. Defaults to 5.

    Raises:
        HTTPException: _description_
    """

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    pr_data = body.get("pr_data")
    candidate_nodes = body.get("candidate_nodes")

    if not pr_data or not candidate_nodes:
        raise HTTPException(status_code=400, detail="Missing pr_data or candidate_nodes")

    results = RERANKER.rerank(
        pr_data=pr_data,
        candidate_nodes=candidate_nodes,
        top_k=top_k
    )
    return {
        "count": len(results),
        "results": results
    }

if __name__ == '__main__':
    uvicorn.run('main:app', host='0.0.0.0', port=8001)
