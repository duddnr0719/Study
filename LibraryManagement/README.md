# 도서관리 시스템 (LibraryManagement)

13장 XML 기반 도서관리 프로그램을 **MySQL 데이터베이스** 기반으로 변환한 프로젝트입니다.

---

## 데이터베이스 접속 정보

| 항목 | 값 |
|------|----|
| 서버 | localhost |
| 사용자 | root |
| 비밀번호 | 1111 |
| 데이터베이스 | **sch** |

---

## 사용 테이블

| 테이블 이름 | 설명 |
|-------------|------|
| **book** | 도서 정보 |
| **user** | 회원 정보 |
| **borrow** | 대출/반납 내역 |

> ※ 프로그램 최초 실행 시 `sch` 데이터베이스와 3개 테이블이 **자동으로 생성**됩니다.

---

## 테이블 스키마

### book 테이블
```sql
CREATE TABLE book (
    book_id      INT AUTO_INCREMENT PRIMARY KEY,
    title        VARCHAR(200) NOT NULL,
    author       VARCHAR(100) DEFAULT '',
    publisher    VARCHAR(100) DEFAULT '',
    isbn         VARCHAR(20)  DEFAULT '',
    is_available TINYINT(1)   DEFAULT 1   -- 1: 대출가능, 0: 대출중
);
```

### user 테이블
```sql
CREATE TABLE user (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    name    VARCHAR(50)  NOT NULL,
    phone   VARCHAR(20)  DEFAULT '',
    email   VARCHAR(100) DEFAULT ''
);
```

### borrow 테이블
```sql
CREATE TABLE borrow (
    borrow_id   INT AUTO_INCREMENT PRIMARY KEY,
    book_id     INT  NOT NULL,
    user_id     INT  NOT NULL,
    borrow_date DATE NOT NULL,
    return_date DATE,
    is_returned TINYINT(1) DEFAULT 0,    -- 0: 대출중, 1: 반납완료
    FOREIGN KEY (book_id) REFERENCES book(book_id),
    FOREIGN KEY (user_id) REFERENCES user(user_id)
);
```

---

## 프로젝트 구조

```
LibraryManagement/
├── Program.cs                         # 진입점 (DB 초기화 → MainForm 실행)
├── LibraryManagement.csproj           # 프로젝트 파일 (MySql.Data 8.3.0 포함)
│
├── Database/
│   └── DatabaseManager.cs            # MySQL 연결 관리, DB/테이블 자동 생성
│
├── Models/
│   ├── Book.cs                        # book 테이블 모델
│   ├── User.cs                        # user 테이블 모델
│   └── Borrow.cs                      # borrow 테이블 모델
│
├── Repositories/
│   ├── BookRepository.cs              # book CRUD (조회/추가/삭제/상태변경)
│   ├── UserRepository.cs             # user CRUD (조회/추가/삭제)
│   └── BorrowRepository.cs           # borrow 대출등록/반납처리 (트랜잭션)
│
└── Forms/
    ├── MainForm.cs                    # 메인 메뉴
    ├── BookForm.cs                    # 도서 관리 화면
    ├── BookAddForm.cs                 # 도서 추가 다이얼로그
    ├── UserForm.cs                    # 회원 관리 화면
    ├── UserAddForm.cs                 # 회원 추가 다이얼로그
    ├── BorrowForm.cs                  # 대출/반납 관리 화면
    └── BorrowAddForm.cs               # 대출 등록 다이얼로그
```

---

## 빌드 및 실행 방법

### 사전 조건
- Windows OS
- .NET 8 SDK 설치
- MySQL 서버 실행 중 (root / 1111)

### 실행
```
dotnet run
```
또는 Visual Studio에서 프로젝트 열기 후 F5

---

## XML → MySQL 변경 요약

| 구분 | 기존 (XML) | 변경 후 (MySQL) |
|------|-----------|-----------------|
| 데이터 저장 | XML 파일 읽기/쓰기 | SQL INSERT/UPDATE/DELETE |
| 데이터 조회 | XmlDocument 파싱 | SQL SELECT + MySqlDataReader |
| 데이터 무결성 | 수동 관리 | 외래키(FK) + 트랜잭션 |
| 대출/반납 원자성 | 직접 구현 | MySqlTransaction으로 보장 |
