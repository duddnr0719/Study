namespace LibraryManagement.Models
{
    /// <summary>
    /// 도서 모델 — 교재 13장 Book 클래스 필드 그대로 유지
    /// book 테이블과 매핑
    /// </summary>
    public class Book
    {
        public string   Isbn       { get; set; } = "";
        public string   Name       { get; set; } = "";
        public string   Publisher  { get; set; } = "";
        public int      Page       { get; set; }

        // 대출 정보 (book 테이블 내 컬럼으로 저장)
        public bool     isBorrowed { get; set; }
        public DateTime BorrowedAt { get; set; }
        public int      UserId     { get; set; }
        public string   UserName   { get; set; } = "";
    }
}
