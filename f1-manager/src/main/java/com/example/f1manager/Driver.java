package com.example.f1manager;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.Id;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Getter @Setter
@NoArgsConstructor

public class Driver {
    @Id @GeneratedValue
    private Long id;
    private String name;
    private String team;
    private int points;
}
