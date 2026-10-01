# from sentence_transformers import SentenceTransformer
import os, re, glob, json
from pathlib import Path
from typing import List, Optional
import requests

STOPWORDS_DICT = set()

CURRENT_DIR = Path(os.path.dirname(__file__)).absolute()

def load_stopwords():
    try:
        pattern = os.path.join(CURRENT_DIR, "../data/stopwords_*.txt")
        files = glob.glob(pattern)
        for f in files:
            with open(f, 'r', encoding='utf-8') as fn:
                words = [line.strip() for line in fn if line.strip()]
                STOPWORDS_DICT.update(words)
        print(f"불용어 로드 완료: {len(STOPWORDS_DICT)}개")
    except Exception as e:
        print(f"STOPWORD 불러오기 중 오류: {e}")

# init stopwords
load_stopwords()


class NLPKeywordExtractDispatcher:
    """정책 텍스트에서 핵심 키워드를 추출하는 API를 호출한다."""
    
    def __init__(self):
        self._nlp_endpoint = os.getenv('NLP_ENGINE_API_ENDPOINT', '')
        assert self._nlp_endpoint.strip() != '', "NLP_ENGINE_API_ENDPOINT를 지정해야 합니다."
    
    def extract_keywords(
        self, 
        content: str, 
        top_n: int = 10, 
        diversity: float = 0.45
    ):
        """
        [POST] ...azurecontainerapps.io/api/engine/extract-keywords?top_n=20&tokenize=true&ngram_end=1&diversity=0.7  

        **POST BODY:**  
        ```json
        {
            "text": "이미지가 이미 구름(ACR) 위에 올라가 있으므로, 소스 코드 없이 이미지 이름만 지정해서 배포합니다. 이 방식이 인증 문제나 빌드 에러를 피하기 훨씬 깔끔합니다."
        }
        ```

        **RESULT:**  
        ```json
        {
            "keywords": [
                "이미지",
                "구름",
                "코드",
                "인증",
                "배포"
                ...
            ]
        }
        ```

        주어진 텍스트에서 명사를 추출하고 KeyBERT를 활용해 핵심 키워드를 반환합니다.
        
        Args:
            content (str): 키워드를 추출할 정책 텍스트 본문
            top_n (int): 추출할 기본 키워드 개수
            diversity (float): MMR 알고리즘의 다양성 지수 (0~1, 높을수록 다양한 키워드 추출)
            
        Returns:
            List[str]: 추출된 최종 키워드 리스트
        """
        # 1. 예외 처리: 입력 텍스트가 비어있을 경우
        if not content or not content.strip():
            return []
        try:
            res = requests.post(
                f"{self._nlp_endpoint.rstrip('/')}/api/engine/extract-keywords", 
                json={'text': str(content)}, 
                params={
                    'top_n': top_n,
                    'diversity': diversity,
                    'tokenize': False,
                    'ngram_end': 2
                }
            )
            res.raise_for_status()
            data = res.json()["keywords"]
        except Exception as e:
            print(f"Error during extract keyword by nlp api: {e}")
            raise
        return data

    def tokenize(self, content: str) -> list[dict]:
        if not content or not content.strip():
            return []
        try:
            res = requests.post(
                f"{self._nlp_endpoint.rstrip('/')}/api/engine/tokenize", 
                json={'text': str(content)}, 
            )
            res.raise_for_status()
            data = res.json()
        except Exception as e:
            print(f"Error during extract keyword by nlp api: {e}")
            raise
        return data
    
    def rerank(self, pr_data, candidate_nodes, top_k: int=5):
        """Rerank 수행후 반환 받는다.
        
        Args:
            pr_data (dict): PR Data 입력.
            candidate_nodes (list[dict]): 지식 노드 데이터 입력
        """
        try:
            res = requests.post(
                f"{self._nlp_endpoint.rstrip('/')}/api/engine/rerank", 
                params={
                    'top_k': top_k
                },
                json={
                    'pr_data': pr_data,
                    'candidate_nodes': candidate_nodes
                }
            )
            res.raise_for_status()
            data = res.json()
        except Exception as e:
            print(f"Error during extract keyword by nlp api: {e}")
            raise
        return data


def extract_keywords_in_policies_list(
        policies: list,
        key_name_to_save_keywords: str='keywords_ext', 
        preprocess=True
    ):
    """content 본문에서 워드를 추출하고 데이터에 포함시킵니다."""
    keyword_extract_dispatcher = NLPKeywordExtractDispatcher()
    preprocessor = KoreanPreprocessor(keyword_extract_dispatcher)
    pmax = len(policies)
    for i, p in enumerate(policies, start=1):
        # text =  f"{p['title']} \n {p['content']}"
        text =  f"{p['content']}"
        if preprocess:
            text = preprocessor.clean_text_for_keywords_v2(text)      # 3.5/5 - stopword 사용
        print(f'     {i} of {pmax} - Keyword Extract by external API: {p['title'][:10]}...  | Preprocessed: {preprocess}')
        p[key_name_to_save_keywords] = [
                preprocessor.clean_underbar_to_space(k)
                for k in keyword_extract_dispatcher.extract_keywords(text)
            ]
    return policies


class KoreanPreprocessor:
    def __init__(self, api_dispatcher: NLPKeywordExtractDispatcher):
        self._api_dispatcher = api_dispatcher
        self._stopwords_set = STOPWORDS_DICT

    @staticmethod
    def clean_underbar_to_space(text: str, rep=' '):
        if '_' in text:
            text = text.replace('_', rep)
        return text

    def clean_text_for_keywords_v2(self, text: str, prevent_ngram_sep='----') -> str:
        if not text or not text.strip():
            return ""

        tokens = self._api_dispatcher.tokenize(text)

        valid_words = []
        temp_compound = []

        for t in tokens:
            tag = t['tag']
            word = t['form']

            if tag.startswith(('NN', 'SL', 'MM')):
                if len(word) > 1 and word not in self._stopwords_set:
                    temp_compound.append(word)
                    continue

            if tag in ('SF', 'SE'):  # 마침표, 느낌표 등
                if temp_compound:
                    valid_words.append("_".join(temp_compound))
                    temp_compound = []
                valid_words.append(prevent_ngram_sep)  # 의미 단절 토큰
                continue

            if temp_compound:
                valid_words.append("_".join(temp_compound))
                temp_compound = []

        if temp_compound:
            valid_words.append("_".join(temp_compound))

        cleaned = []
        prev = None
        for w in valid_words:
            if w == prevent_ngram_sep and prev == prevent_ngram_sep:
                continue
            cleaned.append(w)
            prev = w

        return " ".join(cleaned)
    

    def deprecated_clean_text_for_keywords(
            self, text: str, 
            index=None, 
            keep_space_on_ignored_token=True,
            keep_space_rep='---'
    ) -> str:
        """
        텍스트에서 조사, 접속사, 불용어를 제거하고 핵심 명사만 추출하여 공백으로 이어진 문자열을 반환합니다.

        Params:
            :keep_space_on_ignored_token: (bool) 추후 N-Gram을 위해 생략된 토큰/글자는 공백을 남긴다. 
        """
        raise NotImplementedError()
        if not text or not text.strip():
            return ""
        
        tokens = self._api_dispatcher.tokenize(text)
        # with open(f'./tkn_result_test_{index}.json', 'w', encoding='utf-8') as f:
        #     f.write(json.dumps(tokens, ensure_ascii=False, indent=4))

        valid_words = []

        for t in tokens:
            # 1. 품사 필터링: NNG(일반명사), NNP(고유명사), SL(알파벳/외래어)만 허용
            # 조사(J), 어미(E), 의존명사(NNB), 대명사(NP), 접속사 등은 여기서 모두 탈락됨
            if t['tag'] in ('NNG', 'NNP', 'SL'):
                word = t['form']
                if len(word) > 1:
                    if word not in self._stopwords_set:
                        valid_words.append(word)
                        continue
            if keep_space_on_ignored_token:
                valid_words.append(keep_space_rep)
        return " ".join(valid_words)
