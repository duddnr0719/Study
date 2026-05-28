namespace LibraryManagement.Models
{
    // book 테이블과 매핑되는 도서 모델
    public class Book
    {
        public int BookId { get; set; }
        public string Title { get; set; } = string.Empty;
        public string Author { get; set; } = string.Empty;
        public string Publisher { get; set; } = string.Empty;
        public string Isbn { get; set; } = string.Empty;
        public bool IsAvailable { get; set; } = true;

        public string AvailableText => IsAvailable ? "대출가능" : "대출중";

        public override string ToString() => Title;
    }
}
