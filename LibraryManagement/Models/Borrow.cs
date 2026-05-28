namespace LibraryManagement.Models
{
    // borrow 테이블과 매핑되는 대출 모델
    public class Borrow
    {
        public int BorrowId { get; set; }
        public int BookId { get; set; }
        public int UserId { get; set; }
        public string BookTitle { get; set; } = string.Empty;   // book.title JOIN
        public string UserName { get; set; } = string.Empty;    // user.name JOIN
        public DateTime BorrowDate { get; set; }
        public DateTime? ReturnDate { get; set; }
        public bool IsReturned { get; set; }

        public string StatusText => IsReturned ? "반납완료" : "대출중";
        public string ReturnDateText => ReturnDate.HasValue
            ? ReturnDate.Value.ToString("yyyy-MM-dd") : "-";
    }
}
