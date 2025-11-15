from __future__ import annotations
from typing import Dict, List
from sqlalchemy.orm import Session

from app.models.category import Category, CategoryName

CATEGORY_SEED: List[Dict] = [
    # 상위 분류 예시
    {
        "code": "physics",
        "depth": 1,
        "names": {"en": "Physics", "ko": "물리학"},
    },
    {
        "code": "cs",
        "depth": 1,
        "names": {"en": "Computer Science", "ko": "컴퓨터 과학"},
    },
    {
        "code": "math",
        "depth": 1,
        "names": {"en": "Mathematics", "ko": "수학"},
    },
    {
        "code": "q-bio",
        "depth": 1,
        "names": {"en": "Quantitative Biology", "ko": "계량 생물학"},
    },
    {
        "code": "q-fin",
        "depth": 1,
        "names": {"en": "Quantitative Finance", "ko": "계량 금융"},
    },
    {
        "code": "econ",
        "depth": 1,
        "names": {"en": "Economics", "ko": "경제학"},
    },
    {
        "code": "stat",
        "depth": 1,
        "names": {"en": "Statistics", "ko": "통계학"},
    },
    {
        "code": "eess",
        "depth": 1,
        "names": {"en": "Electrical Engineering and Systems Science", "ko": "전기공학·시스템 과학"},
    },
    {
        "code": "nlin",
        "depth": 1,
        "names": {"en": "Nonlinear Sciences", "ko": "비선형 과학"},
    },

    # ---------------- physics / astro-ph / cond-mat ----------------
    {"code": "acc-phys", "parent": "physics", "depth": 2,
     "names": {"en": "Accelerator Physics (legacy)", "ko": "가속기 물리학 (구 분류)"}},
    {"code": "astro-ph", "parent": "physics", "depth": 2,
     "names": {"en": "Astrophysics", "ko": "천체물리학"}},
    {"code": "astro-ph.CO", "parent": "astro-ph", "depth": 3,
     "names": {"en": "Cosmology and Extragalactic Astrophysics", "ko": "우주론·외은하 천체물리"}},
    {"code": "astro-ph.EP", "parent": "astro-ph", "depth": 3,
     "names": {"en": "Earth and Planetary Astrophysics", "ko": "지구·행성 천체물리"}},
    {"code": "astro-ph.GA", "parent": "astro-ph", "depth": 3,
     "names": {"en": "Galaxy Astrophysics", "ko": "은하 천체물리"}},
    {"code": "astro-ph.HE", "parent": "astro-ph", "depth": 3,
     "names": {"en": "High Energy Astrophysical Phenomena", "ko": "고에너지 천체물리 현상"}},
    {"code": "astro-ph.IM", "parent": "astro-ph", "depth": 3,
     "names": {"en": "Instrumentation and Methods", "ko": "관측 장비·천문 관측 기법"}},
    {"code": "astro-ph.SR", "parent": "astro-ph", "depth": 3,
     "names": {"en": "Solar and Stellar Astrophysics", "ko": "태양·항성 천체물리"}},

    {"code": "atom-ph", "parent": "physics", "depth": 2,
     "names": {"en": "Atomic Physics (legacy)", "ko": "원자 물리 (구 분류)"}},
    {"code": "chem-ph", "parent": "physics", "depth": 2,
     "names": {"en": "Chemical Physics (legacy)", "ko": "화학 물리 (구 분류)"}},

    {"code": "cond-mat", "parent": "physics", "depth": 2,
     "names": {"en": "Condensed Matter", "ko": "응집물질 물리"}},
    {"code": "cond-mat.dis-nn", "parent": "cond-mat", "depth": 3,
     "names": {"en": "Disordered Systems and Neural Networks", "ko": "무질서계·신경망"}},
    {"code": "cond-mat.mes-hall", "parent": "cond-mat", "depth": 3,
     "names": {"en": "Mesoscale and Nanoscale Physics", "ko": "메조·나노 구조 물리"}},
    {"code": "cond-mat.mtrl-sci", "parent": "cond-mat", "depth": 3,
     "names": {"en": "Materials Science", "ko": "재료 과학"}},
    {"code": "cond-mat.other", "parent": "cond-mat", "depth": 3,
     "names": {"en": "Other Condensed Matter", "ko": "기타 응집물질"}},
    {"code": "cond-mat.quant-gas", "parent": "cond-mat", "depth": 3,
     "names": {"en": "Quantum Gases", "ko": "양자 기체"}},
    {"code": "cond-mat.soft", "parent": "cond-mat", "depth": 3,
     "names": {"en": "Soft Condensed Matter", "ko": "소프트매터(연성 물질)"}},
    {"code": "cond-mat.stat-mech", "parent": "cond-mat", "depth": 3,
     "names": {"en": "Statistical Mechanics", "ko": "통계역학"}},
    {"code": "cond-mat.str-el", "parent": "cond-mat", "depth": 3,
     "names": {"en": "Strongly Correlated Electrons", "ko": "강상관 전자계"}},
    {"code": "cond-mat.supr-con", "parent": "cond-mat", "depth": 3,
     "names": {"en": "Superconductivity", "ko": "초전도"}},

    {"code": "gr-qc", "parent": "physics", "depth": 2,
     "names": {"en": "General Relativity and Quantum Cosmology", "ko": "일반상대론·양자우주론"}},
    {"code": "hep-ex", "parent": "physics", "depth": 2,
     "names": {"en": "High Energy Physics - Experiment", "ko": "고에너지 물리 실험"}},
    {"code": "hep-lat", "parent": "physics", "depth": 2,
     "names": {"en": "High Energy Physics - Lattice", "ko": "고에너지 물리 격자 계산"}},
    {"code": "hep-ph", "parent": "physics", "depth": 2,
     "names": {"en": "High Energy Physics - Phenomenology", "ko": "고에너지 물리 현상론"}},
    {"code": "hep-th", "parent": "physics", "depth": 2,
     "names": {"en": "High Energy Physics - Theory", "ko": "고에너지 이론물리"}},
    {"code": "math-ph", "parent": "physics", "depth": 2,
     "names": {"en": "Mathematical Physics", "ko": "수리물리"}},
    {"code": "mtrl-th", "parent": "cond-mat", "depth": 3,
     "names": {"en": "Materials Theory (legacy)", "ko": "재료 이론 (구 분류)"}},
    {"code": "nucl-ex", "parent": "physics", "depth": 2,
     "names": {"en": "Nuclear Experiment", "ko": "핵물리 실험"}},
    {"code": "nucl-th", "parent": "physics", "depth": 2,
     "names": {"en": "Nuclear Theory", "ko": "핵물리 이론"}},

    {"code": "physics.acc-ph", "parent": "physics", "depth": 2,
     "names": {"en": "Accelerator Physics", "ko": "가속기 물리"}},
    {"code": "physics.ao-ph", "parent": "physics", "depth": 2,
     "names": {"en": "Atmospheric and Oceanic Physics", "ko": "대기·해양 물리"}},
    {"code": "physics.app-ph", "parent": "physics", "depth": 2,
     "names": {"en": "Applied Physics", "ko": "응용 물리"}},
    {"code": "physics.atm-clus", "parent": "physics", "depth": 2,
     "names": {"en": "Atomic and Molecular Clusters", "ko": "원자·분자 클러스터"}},
    {"code": "physics.atom-ph", "parent": "physics", "depth": 2,
     "names": {"en": "Atomic Physics", "ko": "원자 물리"}},
    {"code": "physics.bio-ph", "parent": "physics", "depth": 2,
     "names": {"en": "Biological Physics", "ko": "생물 물리"}},
    {"code": "physics.chem-ph", "parent": "physics", "depth": 2,
     "names": {"en": "Chemical Physics", "ko": "화학 물리"}},
    {"code": "physics.class-ph", "parent": "physics", "depth": 2,
     "names": {"en": "Classical Physics", "ko": "고전 물리"}},
    {"code": "physics.comp-ph", "parent": "physics", "depth": 2,
     "names": {"en": "Computational Physics", "ko": "계산 물리"}},
    {"code": "physics.data-an", "parent": "physics", "depth": 2,
     "names": {"en": "Data Analysis, Statistics and Probability", "ko": "데이터 분석·통계·확률"}},
    {"code": "physics.ed-ph", "parent": "physics", "depth": 2,
     "names": {"en": "Physics Education", "ko": "물리 교육"}},
    {"code": "physics.flu-dyn", "parent": "physics", "depth": 2,
     "names": {"en": "Fluid Dynamics", "ko": "유체 역학"}},
    {"code": "physics.gen-ph", "parent": "physics", "depth": 2,
     "names": {"en": "General Physics", "ko": "일반 물리"}},
    {"code": "physics.geo-ph", "parent": "physics", "depth": 2,
     "names": {"en": "Geophysics", "ko": "지구물리"}},
    {"code": "physics.hist-ph", "parent": "physics", "depth": 2,
     "names": {"en": "History and Philosophy of Physics", "ko": "물리학사·과학철학"}},
    {"code": "physics.ins-det", "parent": "physics", "depth": 2,
     "names": {"en": "Instrumentation and Detectors", "ko": "계측기·검출기"}},
    {"code": "physics.med-ph", "parent": "physics", "depth": 2,
     "names": {"en": "Medical Physics", "ko": "의학 물리"}},
    {"code": "physics.optics", "parent": "physics", "depth": 2,
     "names": {"en": "Optics", "ko": "광학"}},
    {"code": "physics.plasm-ph", "parent": "physics", "depth": 2,
     "names": {"en": "Plasma Physics", "ko": "플라즈마 물리"}},
    {"code": "physics.pop-ph", "parent": "physics", "depth": 2,
     "names": {"en": "Popular Physics", "ko": "대중 물리"}},
    {"code": "physics.soc-ph", "parent": "physics", "depth": 2,
     "names": {"en": "Physics and Society", "ko": "사회물리"}},
    {"code": "physics.space-ph", "parent": "physics", "depth": 2,
     "names": {"en": "Space Physics", "ko": "우주 물리"}},

    {"code": "plasm-ph", "parent": "physics", "depth": 2,
     "names": {"en": "Plasma Physics (legacy)", "ko": "플라즈마 물리 (구 분류)"}},
    {"code": "quant-ph", "parent": "physics", "depth": 2,
     "names": {"en": "Quantum Physics", "ko": "양자 물리"}},
    {"code": "supr-con", "parent": "cond-mat", "depth": 3,
     "names": {"en": "Superconductivity (legacy)", "ko": "초전도 (구 분류)"}},
    {"code": "ao-sci", "parent": "physics", "depth": 2,
     "names": {"en": "Atmospheric and Oceanic Sciences (legacy)", "ko": "대기·해양 과학 (구 분류)"}},

    # ---------------- Computer Science (cs) ----------------
    {"code": "cs", "depth": 1,
     "names": {"en": "Computer Science", "ko": "컴퓨터 과학"}},
    {"code": "cs.AI", "parent": "cs", "depth": 2,
     "names": {"en": "Artificial Intelligence", "ko": "인공지능"}},
    {"code": "cs.AR", "parent": "cs", "depth": 2,
     "names": {"en": "Hardware Architecture", "ko": "컴퓨터 아키텍처"}},
    {"code": "cs.CC", "parent": "cs", "depth": 2,
     "names": {"en": "Computational Complexity", "ko": "계산 복잡도"}},
    {"code": "cs.CE", "parent": "cs", "depth": 2,
     "names": {"en": "Computational Engineering, Finance, and Science", "ko": "계산 공학·계산 금융·계산 과학"}},
    {"code": "cs.CG", "parent": "cs", "depth": 2,
     "names": {"en": "Computational Geometry", "ko": "계산 기하"}},
    {"code": "cs.CL", "parent": "cs", "depth": 2,
     "names": {"en": "Computation and Language", "ko": "자연어 처리(계산 언어학)"}},
    {"code": "cs.CR", "parent": "cs", "depth": 2,
     "names": {"en": "Cryptography and Security", "ko": "암호·보안"}},
    {"code": "cs.CV", "parent": "cs", "depth": 2,
     "names": {"en": "Computer Vision and Pattern Recognition", "ko": "컴퓨터 비전·패턴 인식"}},
    {"code": "cs.CY", "parent": "cs", "depth": 2,
     "names": {"en": "Computers and Society", "ko": "컴퓨터와 사회"}},
    {"code": "cs.DB", "parent": "cs", "depth": 2,
     "names": {"en": "Databases", "ko": "데이터베이스"}},
    {"code": "cs.DC", "parent": "cs", "depth": 2,
     "names": {"en": "Distributed, Parallel, and Cluster Computing", "ko": "분산·병렬·클러스터 컴퓨팅"}},
    {"code": "cs.DL", "parent": "cs", "depth": 2,
     "names": {"en": "Digital Libraries", "ko": "디지털 라이브러리"}},
    {"code": "cs.DM", "parent": "cs", "depth": 2,
     "names": {"en": "Discrete Mathematics", "ko": "이산수학"}},
    {"code": "cs.DS", "parent": "cs", "depth": 2,
     "names": {"en": "Data Structures and Algorithms", "ko": "자료구조·알고리즘"}},
    {"code": "cs.ET", "parent": "cs", "depth": 2,
     "names": {"en": "Emerging Technologies", "ko": "신흥 기술"}},
    {"code": "cs.FL", "parent": "cs", "depth": 2,
     "names": {"en": "Formal Languages and Automata Theory", "ko": "형식언어·오토마타"}},
    {"code": "cs.GL", "parent": "cs", "depth": 2,
     "names": {"en": "General Literature", "ko": "일반 문헌"}},
    {"code": "cs.GR", "parent": "cs", "depth": 2,
     "names": {"en": "Graphics", "ko": "컴퓨터 그래픽스"}},
    {"code": "cs.GT", "parent": "cs", "depth": 2,
     "names": {"en": "Computer Science and Game Theory", "ko": "알고리즘·게임이론(컴퓨터 과학 관점)"}},
    {"code": "cs.HC", "parent": "cs", "depth": 2,
     "names": {"en": "Human-Computer Interaction", "ko": "인간-컴퓨터 상호작용(HCI)"}},
    {"code": "cs.IR", "parent": "cs", "depth": 2,
     "names": {"en": "Information Retrieval", "ko": "정보 검색"}},
    {"code": "cs.IT", "parent": "cs", "depth": 2,
     "names": {"en": "Information Theory", "ko": "정보 이론"}},
    {"code": "cs.LG", "parent": "cs", "depth": 2,
     "names": {"en": "Machine Learning", "ko": "머신러닝"}},
    {"code": "cs.LO", "parent": "cs", "depth": 2,
     "names": {"en": "Logic in Computer Science", "ko": "논리와 계산"}},
    {"code": "cs.MA", "parent": "cs", "depth": 2,
     "names": {"en": "Multiagent Systems", "ko": "다중 에이전트 시스템"}},
    {"code": "cs.MM", "parent": "cs", "depth": 2,
     "names": {"en": "Multimedia", "ko": "멀티미디어"}},
    {"code": "cs.MS", "parent": "cs", "depth": 2,
     "names": {"en": "Mathematical Software", "ko": "수학 소프트웨어"}},
    {"code": "cs.NA", "parent": "cs", "depth": 2,
     "names": {"en": "Numerical Analysis", "ko": "수치 해석(컴퓨터 과학 관점)"}},
    {"code": "cs.NE", "parent": "cs", "depth": 2,
     "names": {"en": "Neural and Evolutionary Computing", "ko": "신경망·진화 계산"}},
    {"code": "cs.NI", "parent": "cs", "depth": 2,
     "names": {"en": "Networking and Internet Architecture", "ko": "네트워크·인터넷 아키텍처"}},
    {"code": "cs.OH", "parent": "cs", "depth": 2,
     "names": {"en": "Other Computer Science", "ko": "기타 컴퓨터 과학"}},
    {"code": "cs.OS", "parent": "cs", "depth": 2,
     "names": {"en": "Operating Systems", "ko": "운영체제"}},
    {"code": "cs.PF", "parent": "cs", "depth": 2,
     "names": {"en": "Performance", "ko": "성능 평가"}},
    {"code": "cs.PL", "parent": "cs", "depth": 2,
     "names": {"en": "Programming Languages", "ko": "프로그래밍 언어"}},
    {"code": "cs.RO", "parent": "cs", "depth": 2,
     "names": {"en": "Robotics", "ko": "로봇공학"}},
    {"code": "cs.SC", "parent": "cs", "depth": 2,
     "names": {"en": "Symbolic Computation", "ko": "기호 계산"}},
    {"code": "cs.SD", "parent": "cs", "depth": 2,
     "names": {"en": "Sound", "ko": "오디오·음향 처리"}},
    {"code": "cs.SE", "parent": "cs", "depth": 2,
     "names": {"en": "Software Engineering", "ko": "소프트웨어 공학"}},
    {"code": "cs.SI", "parent": "cs", "depth": 2,
     "names": {"en": "Social and Information Networks", "ko": "사회·정보 네트워크"}},
    {"code": "cs.SY", "parent": "cs", "depth": 2,
     "names": {"en": "Systems and Control", "ko": "시스템·제어"}},

    {"code": "cmp-lg", "parent": "cs", "depth": 2,
     "names": {"en": "Computational Linguistics (legacy)", "ko": "계산 언어학 (구 분류)"}},

    #
    # 나머지 math / q-bio / q-fin / econ / stat / eess / nlin 항목도
    # 동일 패턴으로 추가하면 된다.
    #
]


def seed_categories(db: Session) -> None:
    """
    CATEGORY_SEED 기준으로 categories / category_names를 upsert.
    - 이미 존재하는 code는 이름/부모/깊이를 갱신
    - 없는 code는 생성
    """
    existing_by_code: Dict[str, Category] = {
        c.code: c for c in db.query(Category).all()
    }

    def _get_or_create_category(item: Dict) -> Category:
        code = item["code"]
        cat = existing_by_code.get(code)
        parent_obj = None

        parent_code = item.get("parent")
        if parent_code:
            parent_obj = existing_by_code.get(parent_code)
            if not parent_obj:
                raise ValueError(f"Parent category '{parent_code}' for '{code}' not found")

        if cat is None:
            cat = Category(
                code=code,
                parent_id=parent_obj.id if parent_obj else None,
                depth=item.get("depth", 1),
                sort_order=0,
            )
            db.add(cat)
            db.flush()  # id 생성
            existing_by_code[code] = cat
        else:
            cat.parent_id = parent_obj.id if parent_obj else None
            cat.depth = item.get("depth", cat.depth)

        return cat

    for item in CATEGORY_SEED:
        cat = _get_or_create_category(item)

        for locale, name in item.get("names", {}).items():
            cname = (
                db.query(CategoryName)
                .filter(
                    CategoryName.category_id == cat.id,
                    CategoryName.locale == locale,
                )
                .first()
            )
            if cname:
                cname.name = name
            else:
                db.add(
                    CategoryName(
                        category_id=cat.id,
                        locale=locale,
                        name=name,
                    )
                )

    db.commit()