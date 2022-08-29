from datetime import datetime
import win32com.client
import configparser
import pythoncom
import time


# class XASessionEventHandler:
class XASession:

    # 로그인 상태를 확인하기 위한 클래스 변수
    login_state = 0

    # 로그인 시도 후 호출되는 이벤트
    def OnLogin(self, code, msg):
        # code가 0000이면 로그인 성공
        if code == "0000":
            # print("로그인 성공")
            print(code, msg)
            XASession.login_state = 1
        else:
            # print("로그인 실패")
            print(code, msg)

    # 서버와 연결이 끊어지면 발생하는 이벤트
    def OnDistconnect(self):
        print("Session disconnected")
        XASession.login_state = 0


# class XAQueryEventHandler:
class XAQuery:

    RES_PATH = "C:\\eBEST\\xingAPI\\Res\\"
    tr_run_state = 0

    def OnReceiveData(self, code):
        print("OnReceiveData", code)
        XAQuery.tr_run_state = 1

    def OnReceiveMessage(self, error, code, message):
        print("OnReceiveMessage", error, code, message)


class EBest:

    QUERY_LIMIT_10MIN = 200
    LIMIT_SECONDS = 600  # 10 min

    def __init__(self, mode=None):
        """"
        query_count는 10분당 200개의 TR 수행을 관리하기 위한 리스트
        :param mode:str - 모의서버는 "DEMO" 실서버는 "PROD"로 구분
        """
        if mode not in ["PROD", "DEMO"]:
            raise Exception("Need to run_mode(PROD or DEMO)")

        run_mode = "EBEST_" + mode
        config = configparser.ConfigParser()
        # config.read("conf/config.ini")
        config.read("../conf/config.ini")
        # config.sections()
        self.user = config[run_mode]["user"]
        self.password = config[run_mode]["password"]
        self.cert_password = config[run_mode]["cert_password"]
        self.host = config[run_mode]["host"]
        self.port = config[run_mode]["port"]
        self.account = config[run_mode]["account"]

        self.xa_session_client = win32com.client.DispatchWithEvents("XA_Session.XASession", XASession)
        self.query_count = []

    def login(self):
        self.xa_session_client.ConnectServer(self.host, self.port)
        self.xa_session_client.Login(self.user, self.password, self.cert_password, 0, 0)
        # toggled by XASession.OnLogIn & XASession.OnDisconnect
        while XASession.login_state == 0:
            pythoncom.PumpWaitingMessages()

    def logout(self):
        result = self.xa_session_client.Logout()
        if result:
            XASession.login_state = 0
        self.xa_session_client.DisconnectServer()

    def _execute_query(self, res, in_block_name, out_block_name, *out_fields, **in_fields):
        """
        :param res:str            - 리소스 이름(TR)
        :param in_block_name:str  - 인 블록 이름
        :param out_block_name:str - 아웃 블록 이름
        :return result:list       - 결과 리스트
        in_params  = {"gubun": market_code[market]}
        out_params = {"hname", "shcode", "expcode", "etfgubun", "memdan", "gubun", "spac_gubun"}
        result = self._execute_query("t846", "t846InBlock", "t846OutBlock", *out_params, **in_params)
        """
        # Manage the Queried Time Queue
        time.sleep(1)
        print("current query count:", len(self.query_count))
        print(res, in_block_name, out_block_name)
        # when queries are full
        while len(self.query_count) >= EBest.QUERY_LIMIT_10MIN:
            time.sleep(1)
            print("waiting for execute query... current query count:", len(self.query_count))
            # garbage collection
            self.query_count = list(filter(lambda qt: (datetime.today() - qt).total_seconds() < EBest.LIMIT_SECONDS,
                                           self.query_count))

        # Make a Query for Request
        xa_query = win32com.client.DispatchWithEvents("XA_DataSet.XAQuery", XAQuery)
        xa_query.LoadFromResFile(XAQuery.RES_PATH + res + ".res")
        # in_block_name 세팅
        for key, value in in_fields.items():
           xa_query.SetFieldData(in_block_name, key, 0, value)
        errorCode = xa_query.Request(0)

        # Wait for a Message
        waiting_count = 0
        while xa_query.tr_run_state == 0:
            waiting_count += 1
            if waiting_count % 100000 == 0:
                print("Waiting....", self.xa_session_client.GetLastError())
            pythoncom.PumpWaitingMessages()

        # Get the Field Data & Queue the Queried Time
        result = []
        count = xa_query.GetBlockCount(out_block_name)
        for index in range(count):
            item = {}
            # Filter the output
            for field in out_fields:
                value = xa_query.GetFieldData(out_block_name, field, index)
                item[field] = value
            result.append(item)
        XAQuery.tr_run_state = 0
        self.query_count.append(datetime.today())

        # Translate the Field Names
        for item in result:
            for field in list(item.keys()):
                # English -> Korean
                # for each TR
                if getattr(KField, res, None):          # res = t1101
                    block_names = getattr(KField, res)  # , None):
                    # for OutBlock
                    if out_block_name in block_names:   # t1101OutBlock
                        field_hnames = block_names[out_block_name]
                        # for each field
                        if field in field_hnames:
                            # add korean name(field_names[field])
                            item[field_hnames[field]] = item[field]
                            # remove english name
                            item.pop(field)

        return result


    # 주식 종목 조회 (t8436)
    def get_code_list(self, market=None):
        """
        TR t8436            - 코스피, 코스닥의 종목 리스트를 가져온다.
        :param market:str   - 전체(0), 코스피(1), 코스닥(2)
        :return result:list - 시장별 종목 리스트
        """
        if market != "ALL" and market != "KOSPI" and market != "KOSDAQ":
            raise Exception("Need to market param(ALL, KOSPI, KOSDAQ)")

        market_code = {"ALL": "0", "KOSPI": "1", "KOSDAQ": "2"}
        in_params   = {"gubun": market_code[market]}
        out_params  = ["hname", "shcode", "expcode", "etfgubun", "memedan", "gubun", "spac_gubun"]
        result = self._execute_query("t8436", "t8436InBlock", "t8436OutBlock", *out_params, **in_params)
        return result

    # 기간별 주가 (t1305)
    def get_stock_price_by_code(self, code=None, count="1"):
        """
        TR t1305            - 현재 날짜를 기준으로 cnt 만큼 전일의 데이터를 가져온다.
        :param code:str     - 종목코드
        :param count:str    - 이전 데이터 조회 범위(일단위)
        :return result:list - 종목의 최근 가격 정보
        """
        in_params  = {"shcode": code, "dwmcode": "1", "date": "", "idx": "", "cnt": count}
        out_params = ["date", "open", "high", "low", "close", "sign", "change", "diff", "volume", "diff_vol",
                      "chdegree", "sojinrate", "changerate", "fpvolume", "covolume", "value", "ppvolume", "o_sign",
                      "o_change", "o_diff", "h_sign", "h_change", "h_diff", "l_sign", "l_change", "l_diff", "marketcap"]
        result = self._execute_query("t1305", "t1305InBlock", "t1305OutBlock1", *out_params, **in_params)
        # list of dictionaries(size = cnt)
        for item in result:
            # item.update({"code": code})
            # item.update(dict(code=code))
            # item.update(code=code)
            item["code"] = code
        # result = [dict(item, **{"code": code}) for item in result]
        return result


    # 신용거래 동향 (t1921)
    def get_credit_trend_by_code(self, code=None, date=None):
        """
        TR t1921            - 신용거래 동향
        :param code:str     - 종목코드
        :param date:str     - 날짜 (ex: 20190222)
        :return result:list -
        """
        in_params  = {"gubun": "0", "shcode": code, "date": date, "idx": "0"}
        out_params = ["mmdate", "close", "sign", "jchange", "diff", "nvolume", "svolume", "jvolume", "price", "change",
                      "gyrate", "jkrate", "shcode"]
        result = self._execute_query("t1921", "t1921InBlock", "t1921OutBlock1", *out_params, **in_params)
        for item in result:
            item["code"] = code
        return result

    # 외인 기간별/종목별 동향 (t1717)
    def get_agent_trend_by_code(self, code=None, fromdt=None, todt=None):
        """
        TR t1717           - 외인 기관별/종목별 동향
        :param code:str    - 종목코드
        :param fromdt:str  - 조회 시작 날짜
        :param todt:str    - 조회 종료 날짜
        :return result:str - 시장별 종목 리스트
        """
        in_params  = {"gubun": "0", "fromdt": fromdt, "todt": todt, "shcode": code}
        out_params = ["date", "close", "sign", "change", "diff", "volume", "tjj0000_vol", "tjj0001_vol", "tjj0002_vol",
                      "tjj0003_vol", "tjj0004_vol", "tjj0005_vol", "tjj0006_vol", "tjj0007_vol", "tjj0008_vol",
                      "tjj0009_vol", "tjj0010_vol", "tjj0011_vol", "tjj0012_vol", "tjj0013_vol", "tjj0014_vol",
                      "tjj0015_vol", "tjj0016_vol", "tjj0017_vol", "tjj0001_dan", "tjj0002_dan", "tjj0003_dan",
                      "tjj0004_dan", "tjj0005_dan", "tjj0006_dan", "tjj0007_dan", "tjj0008_dan", "tjj0009_dan",
                      "tjj0010_dan", "tjj0011_dan", "tjj0012_dan", "tjj0013_dan", "tjj0014_dan", "tjj0015_dan",
                      "tjj0016_dan", "tjj0017_dan"]
        result = self._execute_query("t1717", "t1717InBlock", "t1717OutBlock", *out_params, **in_params)
        for item in result:
            item["code"] = code
        return result

    # 공매도 추이(t1927)
    def get_short_trend_by_code(self, code=None, sdate=None, edate=None):
        """
        TR t1927           - 공매도 일별추이
        :param code:str    - 종목코드
        :param sdate:str   - 시작일자
        :param edate:str   - 종료일자
        :return result:str - 시장 별 종목 리스트
        """
        in_params  = {"date": sdate, "sdate": sdate, "edate": edate, "shcode": code}
        out_params = ["date", "price", "sign", "change", "diff", "volume", "value",
                      "gm_vo", "gm_va", "gm_per", "gm_avg", "gm_vo_sum"]
        result = self._execute_query("t1927", "t1927InBlock", "t1927OutBlock1", *out_params, **in_params)
        for item in result:
            item["code"] = code
        return result


"""
Translation Table
"""
class KField:

    t1101 = {
        "t1101OutBlock":{
            "hname":"한글명",
            "price":"현재가",
            "sign":"전일대비구분",
            "change":"전일대비",
            "diff":"등락율",
            "volume":"누적거래량",
            "jnilclose":"전일종가",
            "offerho1":"매도호가1",
            "bidho1":"매수호가1",
            "offerrem1":"매도호가수량1",
            "bidrem1":"매수호가수량1",
            "preoffercha1":"직전매도대비수량1",
            "prebidcha1":"직전매수대비수량1",
            "offerho2":"매도호가2",
            "bidho2":"매수호가2",
            "offerrem2":"매도호가수량2",
            "bidrem2":"매수호가수량2",
            "preoffercha2":"직전매도대비수량2",
            "prebidcha2":"직전매수대비수량2",
            "offerho3":"매도호가3",
            "bidho3":"매수호가3",
            "offerrem3":"매도호가수량3",
            "bidrem3":"매수호가수량3",
            "preoffercha3":"직전매도대비수량3",
            "prebidcha3":"직전매수대비수량3",
            "offerho4":"매도호가4",
            "bidho4":"매수호가4",
            "offerrem4":"매도호가수량4",
            "bidrem4":"매수호가수량4",
            "preoffercha4":"직전매도대비수량4",
            "prebidcha4":"직전매수대비수량4",
            "offerho5":"매도호가5",
            "bidho5":"매수호가5",
            "offerrem5":"매도호가수량5",
            "bidrem5":"매수호가수량5",
            "preoffercha5":"직전매도대비수량5",
            "prebidcha5":"직전매수대비수량5",
            "offerho6":"매도호가6",
            "bidho6":"매수호가6",
            "offerrem6":"매도호가수량6",
            "bidrem6":"매수호가수량6",
            "preoffercha6":"직전매도대비수량6",
            "prebidcha6":"직전매수대비수량6",
            "offerho7":"매도호가7",
            "bidho7":"매수호가7",
            "offerrem7":"매도호가수량7",
            "bidrem7":"매수호가수량7",
            "preoffercha7":"직전매도대비수량7",
            "prebidcha7":"직전매수대비수량7",
            "offerho8":"매도호가8",
            "bidho8":"매수호가8",
            "offerrem8":"매도호가수량8",
            "bidrem8":"매수호가수량8",
            "preoffercha8":"직전매도대비수량8",
            "prebidcha8":"직전매수대비수량8",
            "offerho9":"매도호가9",
            "bidho9":"매수호가9",
            "offerrem9":"매도호가수량9",
            "bidrem9":"매수호가수량9",
            "preoffercha9":"직전매도대비수량9",
            "prebidcha9":"직전매수대비수량9",
            "offerho10":"매도호가10",
            "bidho10":"매수호가10",
            "offerrem10":"매도호가수량10",
            "bidrem10":"매수호가수량10",
            "preoffercha10":"직전매도대비수량10",
            "prebidcha10":"직전매수대비수량10",
            "offer":"매도호가수량합",
            "bid":"매수호가수량합",
            "preoffercha":"직전매도대비수량합",
            "prebidcha":"직전매수대비수량합",
            "hotime":"수신시간",
            "yeprice":"예상체결가격",
            "yevolume":"예상체결수량",
            "yesign":"예상체결전일구분",
            "yechange":"예상체결전일대비",
            "yediff":"예상체결등락율",
            "tmoffer":"시간외매도잔량",
            "tmbid":"시간외매수잔량",
            "ho_status":"동시구분",
            "shcode":"단축코드",
            "uplmtprice":"상한가",
            "dnlmtprice":"하한가",
            "open":"시가",
            "high":"고가",
            "low":"저가"
        }
    }

    t1305 = {
        "t1305OutBlock1":{
            "date":"날짜",
            "open":"시가",
            "high":"고가",
            "low":"저가",
            "close":"종가",
            "sign":"전일대비구분",
            "change":"전일대비",
            "diff":"등락율",
            "volume":"누적거래량",
            "diff_vol":"거래증가율",
            "chdegree":"체결강도",
            "sojinrate":"소진율",
            "changerate":"회전율",
            "fpvolume":"외인순매수",
            "covolume":"기관순매수",
            "shcode":"종목코드",
            "value":"누적거래대금",
            "ppvolume":"개인순매수",
            "o_sign":"시가대비구분",
            "o_change":"시가대비",
            "o_diff":"시가기준등락율",
            "h_sign":"고가대비구분",
            "h_change":"고가대비",
            "h_diff":"고가기준등락율",
            "l_sign":"저가대비구분",
            "l_change":"저가대비",
            "l_diff":"저가기준등락율",
            "marketcap":"시가총액"
        }
    }

    t1921 = {
        "t1921OutBlock1":{
            "mmdate":"날짜",
            "close":"종가",
            "sign":"전일대비구분",
            "jchange":"전일대비",
            "diff":"등락율",
            "nvolume":"신규",
            "svolume":"상환",
            "jvolume":"잔고",
            "price":"금액",
            "change":"대비",
            "gyrate":"공여율",
            "jkrate":"잔고율",
            "shcode":"종목코드"
        }
    }

    t8436 = {
        "t8436OutBlock":{
            "hname":"종목명",
            "shcode":"단축코드",
            "expcode":"확장코드",
            "etfgubun":"ETF구분",
            "uplmtprice":"상한가",
            "dnlmtprice":"하한가",
            "jnilclose":"전일가",
            "memedan":"주문수량단위",
            "recprice":"기준가",
            "gubun":"시장구분",
            "bu12gubun":"증권그룹",
            "spac_gubun":"기업인수목적회사여부",
            "filler":"filler(미사용)"
        }
    }

    t1717 = {
        "t1717OutBlock":{
            "date":"일자",
            "close":"종가",
            "sign":"전일대비구분",
            "change":"전일대비",
            "diff":"등락율",
            "volume":"누적거래량",
            "tjj0000_vol":"사모펀드(순매수량)",
            "tjj0001_vol":"증권(순매수량)",
            "tjj0002_vol":"보험(순매수량)",
            "tjj0003_vol":"투신(순매수량)",
            "tjj0004_vol":"은행(순매수량)",
            "tjj0005_vol":"종금(순매수량)",
            "tjj0006_vol":"기금(순매수량)",
            "tjj0007_vol":"기타법인(순매수량)",
            "tjj0008_vol":"개인(순매수량)",
            "tjj0009_vol":"등록외국인(순매수량)",
            "tjj0010_vol":"미등록외국인(순매수량)",
            "tjj0011_vol":"국가외(순매수량)",
            "tjj0018_vol":"기관(순매수량)",
            "tjj0016_vol":"외인계(순매수량)(등록+미등록)",
            "tjj0017_vol":"기타계(순매수량)(기타+국가)",
            "tjj0000_dan":"사모펀드(단가)",
            "tjj0001_dan":"증권(단가)",
            "tjj0002_dan":"보험(단가)",
            "tjj0003_dan":"투신(단가)",
            "tjj0004_dan":"은행(단가)",
            "tjj0005_dan":"종금(단가)",
            "tjj0006_dan":"기금(단가)",
            "tjj0007_dan":"기타법인(단가)",
            "tjj0008_dan":"개인(단가)",
            "tjj0009_dan":"등록외국인(단가)",
            "tjj0010_dan":"미등록외국인(단가)",
            "tjj0011_dan":"국가외(단가)",
            "tjj0018_dan":"기관(단가)",
            "tjj0016_dan":"외인계(단가)(등록+미등록)",
            "tjj0017_dan":"기타계(단가)(기타+국가)"
        }
    }

    t1927 = {
        "t1927OutBlock1":{
            "date":"일자",
            "price":"현재가",
            "sign":"전일대비구분",
            "change":"전일대비",
            "diff":"등락율",
            "volume":"거래량",
            "value":"거래대금",
            "gm_vo":"공매도수량",
            "gm_va":"공매도대금",
            "gm_per":"공매도거래비중",
            "gm_avg":"평균공매도단가",
            "gm_vo_sum":"누적공매도수량"
        }
    }

    t0425 ={
        "t0425OutBlock1":{
            "ordno":"주문번호",
            "expcode":"종목번호",
            "medosu":"구분",
            "qty":"주문수량",
            "price":"주문가격",
            "cheqty":"체결수량",
            "cheprice":"체결가격",
            "ordrem":"미체결잔량",
            "cfmqty":"확인수량",
            "status":"상태",
            "orgordno":"원주문번",
            "ordgb":"유형",
            "ordtime":"주문시간",
            "ordermtd":"주문매체",
            "sysprocseq":"처리순번",
            "hogagb":"호가유형",
            "price1":"현재가",
            "orggb":"주문구분",
            "singb":"신용구분",
            "loandt":"대출일자"
        }
    }

    t8412 = {
        "t8412OutBlock1":{
            "date":"날짜",
            "time":"시간",
            "open":"시가",
            "high":"고가",
            "low":"저가",
            "close":"종가",
            "jdiff_vol":"거래량",
            "value":"거래대금",
            "jongchk":"수정구분",
            "rate":"수정비율",
            "sign":"종가등락구분"
        }
    }

    CSPAQ12200 = {
        "CSPAQ12200OutBlock2":{
            "RecCnt":"레코드갯수",
            "BrnNm":"지점명",
            "AcntNm":"계좌명",
            "MnyOrdAbleAmt":"현금주문가능금액",
            "MnyoutAbleAmt":"출금가능금액",
            "SeOrdAbleAmt":"거래소금액",
            "KdqOrdAbleAmt":"코스닥금액",
            "BalEvalAmt":"잔고평가금액",
            "RcvblAmt":"미수금액",
            "DpsastTotamt":"예탁자산총액",
            "PnlRat":"손익율",
            "InvstOrgAmt":"투자원금",
            "InvstPlAmt":"투자손익금액",
            "CrdtPldgOrdAmt":"신용담보주문금액",
            "Dps":"예수금",
            "SubstAmt":"대용금액",
            "D1Dps":"D1예수금",
            "D2Dps":"D2예수금",
            "MnyrclAmt":"현금미수금액",
            "MgnMny":"증거금현금",
            "MgnSubst":"증거금대용",
            "ChckAmt":"수표금액",
            "SubstOrdAbleAmt":"대용주문가능금액",
            "MgnRat100pctOrdAbleAmt":"증거금률100퍼센트주문가능금액",
            "MgnRat35ordAbleAmt":"증거금률35%주문가능금액",
            "MgnRat50ordAbleAmt":"증거금률50%주문가능금액",
            "PrdaySellAdjstAmt":"전일매도정산금액",
            "PrdayBuyAdjstAmt":"전일매수정산금액",
            "CrdaySellAdjstAmt":"금일매도정산금액",
            "CrdayBuyAdjstAmt":"금일매수정산금액",
            "D1ovdRepayRqrdAmt":"D1연체변제소요금액",
            "D2ovdRepayRqrdAmt":"D2연체변제소요금액",
            "D1PrsmptWthdwAbleAmt":"D1추정인출가능금액",
            "D2PrsmptWthdwAbleAmt":"D2추정인출가능금액",
            "DpspdgLoanAmt":"예탁담보대출금액",
            "Imreq":"신용설정보증금",
            "MloanAmt":"융자금액",
            "ChgAfPldgRat":"변경후담보비율",
            "OrgPldgAmt":"원담보금액",
            "SubPldgAmt":"부담보금액",
            "RqrdPldgAmt":"소요담보금액",
            "OrgPdlckAmt":"원담보부족금액",
            "PdlckAmt":"담보부족금액",
            "AddPldgMny":"추가담보현금",
            "D1OrdAbleAmt":"D1주문가능금액",
            "CrdtIntdltAmt":"신용이자미납금액",
            "EtclndAmt":"기타대여금액",
            "NtdayPrsmptCvrgAmt":"익일추정반대매매금액",
            "OrgPldgSumAmt":"원담보합계금액",
            "CrdtOrdAbleAmt":"신용주문가능금액",
            "SubPldgSumAmt":"부담보합계금액",
            "CrdtPldgAmtMny":"신용담보금현금",
            "CrdtPldgSubstAmt":"신용담보대용금액",
            "AddCrdtPldgMny":"추가신용담보현금",
            "CrdtPldgRuseAmt":"신용담보재사용금액",
            "AddCrdtPldgSubst":"추가신용담보대용",
            "CslLoanAmtdt1":"매도대금담보대출금액",
            "DpslRestrcAmt":"처분제한금액"
        }
    }

    CSPAQ12300 = {
        "CSPAQ12300OutBlock2" :{
            "RecCnt":"레코드갯수",
            "BrnNm":"지점명",
            "AcntNm":"계좌명",
            "MnyOrdAbleAmt":"현금주문가능금액",
            "MnyoutAbleAmt":"출금가능금액",
            "SeOrdAbleAmt":"거래소금액",
            "KdqOrdAbleAmt":"코스닥금액",
            "HtsOrdAbleAmt":"HTS주문가능금액",
            "MgnRat100pctOrdAbleAmt":"증거금률100퍼센트주문가능금액",
            "BalEvalAmt":"잔고평가금액",
            "PchsAmt":"매입금액",
            "RcvblAmt":"미수금액",
            "PnlRat":"손익율",
            "InvstOrgAmt":"투자원금",
            "InvstPlAmt":"투자손익금액",
            "CrdtPldgOrdAmt":"신용담보주문금액",
            "Dps":"예수금",
            "D1Dps":"D1예수금",
            "D2Dps":"D2예수금",
            "OrdDt":"주문일",
            "MnyMgn":"현금증거금액",
            "SubstMgn":"대용증거금액",
            "SubstAmt":"대용금액",
            "PrdayBuyExecAmt":"전일매수체결금액",
            "PrdaySellExecAmt":"전일매도체결금액",
            "CrdayBuyExecAmt":"금일매수체결금액",
            "CrdaySellExecAmt":"금일매도체결금액",
            "EvalPnlSum":"평가손익합계",
            "DpsastTotamt":"예탁자산총액",
            "Evrprc":"제비용",
            "RuseAmt":"재사용금액",
            "EtclndAmt":"기타대여금액",
            "PrcAdjstAmt":"가정산금액",
            "D1CmsnAmt":"D1수수료",
            "D2CmsnAmt":"D2수수료",
            "D1EvrTax":"D1제세금",
            "D2EvrTax":"D2제세금",
            "D1SettPrergAmt":"D1결제예정금액",
            "D2SettPrergAmt":"D2결제예정금액",
            "PrdayKseMnyMgn":"전일KSE현금증거금",
            "PrdayKseSubstMgn":"전일KSE대용증거금",
            "PrdayKseCrdtMnyMgn":"전일KSE신용현금증거금",
            "PrdayKseCrdtSubstMgn":"전일KSE신용대용증거금",
            "CrdayKseMnyMgn":"금일KSE현금증거금",
            "CrdayKseSubstMgn":"금일KSE대용증거금",
            "CrdayKseCrdtMnyMgn":"금일KSE신용현금증거금",
            "CrdayKseCrdtSubstMgn":"금일KSE신용대용증거금",
            "PrdayKdqMnyMgn":"전일코스닥현금증거금",
            "PrdayKdqSubstMgn":"전일코스닥대용증거금",
            "PrdayKdqCrdtMnyMgn":"전일코스닥신용현금증거금",
            "PrdayKdqCrdtSubstMgn":"전일코스닥신용대용증거금",
            "CrdayKdqMnyMgn":"금일코스닥현금증거금",
            "CrdayKdqSubstMgn":"금일코스닥대용증거금",
            "CrdayKdqCrdtMnyMgn":"금일코스닥신용현금증거금",
            "CrdayKdqCrdtSubstMgn":"금일코스닥신용대용증거금",
            "PrdayFrbrdMnyMgn":"전일프리보드현금증거금",
            "PrdayFrbrdSubstMgn":"전일프리보드대용증거금",
            "CrdayFrbrdMnyMgn":"금일프리보드현금증거금",
            "CrdayFrbrdSubstMgn":"금일프리보드대용증거금",
            "PrdayCrbmkMnyMgn":"전일장외현금증거금",
            "PrdayCrbmkSubstMgn":"전일장외대용증거금",
            "CrdayCrbmkMnyMgn":"금일장외현금증거금",
            "CrdayCrbmkSubstMgn":"금일장외대용증거금",
            "DpspdgQty":"예탁담보수량",
            "BuyAdjstAmtD2":"매수정산금(D+2)",
            "SellAdjstAmtD2":"매도정산금(D+2)",
            "RepayRqrdAmtD1":"변제소요금(D+1)",
            "RepayRqrdAmtD2":"변제소요금(D+2)",
            "LoanAmt":"대출금액"
        },
        "CSPAQ12300OutBlock3":{
            "IsuNo":"종목번호",
            "IsuNm":"종목명",
            "SecBalPtnCode":"유가증권잔고유형코드",
            "SecBalPtnNm":"유가증권잔고유형명",
            "BalQty":"잔고수량",
            "BnsBaseBalQty":"매매기준잔고수량",
            "CrdayBuyExecQty":"금일매수체결수량",
            "CrdaySellExecQty":"금일매도체결수량",
            "SellPrc":"매도가",
            "BuyPrc":"매수가",
            "SellPnlAmt":"매도손익금액",
            "PnlRat":"손익율",
            "NowPrc":"현재가",
            "CrdtAmt":"신용금액",
            "DueDt":"만기일",
            "PrdaySellExecPrc":"전일매도체결가",
            "PrdaySellQty":"전일매도수량",
            "PrdayBuyExecPrc":"전일매수체결가",
            "PrdayBuyQty":"전일매수수량",
            "LoanDt":"대출일",
            "AvrUprc":"평균단가",
            "SellAbleQty":"매도가능수량",
            "SellOrdQty":"매도주문수량",
            "CrdayBuyExecAmt":"금일매수체결금액",
            "CrdaySellExecAmt":"금일매도체결금액",
            "PrdayBuyExecAmt":"전일매수체결금액",
            "PrdaySellExecAmt":"전일매도체결금액",
            "BalEvalAmt":"잔고평가금액",
            "EvalPnl":"평가손익",
            "MnyOrdAbleAmt":"현금주문가능금액",
            "OrdAbleAmt":"주문가능금액",
            "SellUnercQty":"매도미체결수량",
            "SellUnsttQty":"매도미결제수량",
            "BuyUnercQty":"매수미체결수량",
            "BuyUnsttQty":"매수미결제수량",
            "UnsttQty":"미결제수량",
            "UnercQty":"미체결수량",
            "PrdayCprc":"전일종가",
            "PchsAmt":"매입금액",
            "RegMktCode":"등록시장코드",
            "LoanDtlClssCode":"대출상세분류코드",
            "DpspdgLoanQty":"예탁담보대출수량"
        }
    }

    CSPAQ13700 = {
        "CSPAQ13700OutBlock3":{
            "OrdDt":"주문일",
            "MgmtBrnNo":"관리지점번호",
            "OrdMktCode":"주문시장코드",
            "OrdNo":"주문번호",
            "OrgOrdNo":"원주문번호",
            "IsuNo":"종목번호",
            "IsuNm":"종목명",
            "BnsTpCode":"매매구분",
            "BnsTpNm":"매매구분",
            "OrdPtnCode":"주문유형코드",
            "OrdPtnNm":"주문유형명",
            "OrdTrxPtnCode":"주문처리유형코드",
            "OrdTrxPtnNm":"주문처리유형명",
            "MrcTpCode":"정정취소구분",
            "MrcTpNm":"정정취소구분명",
            "MrcQty":"정정취소수량",
            "MrcAbleQty":"정정취소가능수량",
            "OrdQty":"주문수량",
            "OrdPrc":"주문가격",
            "ExecQty":"체결수량",
            "ExecPrc":"체결가",
            "ExecTrxTime":"체결처리시각",
            "LastExecTime":"최종체결시각",
            "OrdprcPtnCode":"호가유형코드",
            "OrdprcPtnNm":"호가유형명",
            "OrdCndiTpCode":"주문조건구분",
            "AllExecQty":"전체체결수량",
            "RegCommdaCode":"통신매체코드",
            "CommdaNm":"통신매체명",
            "MbrNo":"회원번호",
            "RsvOrdYn":"예약주문여부",
            "LoanDt":"대출일",
            "OrdTime":"주문시각",
            "OpDrtnNo":"운용지시번호",
            "OdrrId":"주문자ID",
        }
    }

    CSPAT00600 = {
        "CSPAT00600OutBlock1":{
            "RecCnt":"레코드갯수",
            "AcntNo":"계좌번호",
            "InptPwd":"입력비밀번호",
            "IsuNo":"종목번호",
            "OrdQty":"주문수량",
            "OrdPrc":"주문가",
            "BnsTpCode":"매매구분",
            "OrdprcPtnCode":"호가유형코드",
            "PrgmOrdprcPtnCode":"프로그램호가유형코드",
            "StslAbleYn":"공매도가능여부",
            "StslOrdprcTpCode":"공매도호가구분",
            "CommdaCode":"통신매체코드",
            "MgntrnCode":"신용거래코드",
            "LoanDt":"대출일",
            "MbrNo":"회원번호",
            "OrdCndiTpCode":"주문조건구분",
            "StrtgCode":"전략코드",
            "GrpId":"그룹ID",
            "OrdSeqNo":"주문회차",
            "PtflNo":"포트폴리오번호",
            "BskNo":"바스켓번호",
            "TrchNo":"트렌치번호",
            "ItemNo":"아이템번호",
            "OpDrtnNo":"운용지시번호",
            "LpYn":"유동성공급자여부",
            "CvrgTpCode":"반대매매구분"
        },
        "CSPAT00600OutBlock2":{
            "RecCnt":"레코드갯수",
            "OrdNo":"주문번호",
            "OrdTime":"주문시각",
            "OrdMktCode":"주문시장코드",
            "OrdPtnCode":"주문유형코드",
            "ShtnIsuNo":"단축종목번호",
            "MgempNo":"관리사원번호",
            "OrdAmt":"주문금액",
            "SpareOrdNo":"예비주문번호",
            "CvrgSeqno":"반대매매일련번호",
            "RsvOrdNo":"예약주문번호",
            "SpotOrdQty":"실물주문수량",
            "RuseOrdQty":"재사용주문수량",
            "MnyOrdAmt":"현금주문금액",
            "SubstOrdAmt":"대용주문금액",
            "RuseOrdAmt":"재사용주문금액",
            "AcntNm":"계좌명",
            "IsuNm":"종목명"
        }
    }

    CSPAT00800 = {
        "CSPAT00800OutBlock2":{
            "RecCnt":"레코드갯수",
            "OrdNo":"주문번호",
            "PrntOrdNo":"모주문번호",
            "OrdTime":"주문시각",
            "OrdMktCode":"주문시장코드",
            "OrdPtnCode":"주문유형코드",
            "ShtnIsuNo":"단축종목번호",
            "PrgmOrdprcPtnCode":"프로그램호가유형코드",
            "StslOrdprcTpCode":"공매도호가구분",
            "StslAbleYn":"공매도가능여부",
            "MgntrnCode":"신용거래코드",
            "LoanDt":"대출일",
            "CvrgOrdTp":"반대매매주문구분",
            "LpYn":"유동성공급자여부",
            "MgempNo":"관리사원번호",
            "BnsTpCode":"매매구분",
            "SpareOrdNo":"예비주문번호",
            "CvrgSeqno":"반대매매일련번호",
            "RsvOrdNo":"예약주문번호",
            "AcntNm":"계좌명",
            "IsuNm":"종목명"
        }
    }
