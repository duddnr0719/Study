namespace LibraryManagement.Models
{
    // user 테이블과 매핑되는 회원 모델
    public class User
    {
        public int UserId { get; set; }
        public string Name { get; set; } = string.Empty;
        public string Phone { get; set; } = string.Empty;
        public string Email { get; set; } = string.Empty;

        public override string ToString() => Name;
    }
}
