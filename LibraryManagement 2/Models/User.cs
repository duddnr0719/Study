namespace LibraryManagement.Models
{
    /// <summary>
    /// 사용자 모델 — 교재 13장 User 클래스 필드 그대로
    /// user 테이블과 매핑
    /// </summary>
    public class User
    {
        public int    Id   { get; set; }   // 사용자가 직접 입력 (auto_increment 아님)
        public string Name { get; set; } = "";

        public override string ToString() => $"{Id} - {Name}";
    }
}
