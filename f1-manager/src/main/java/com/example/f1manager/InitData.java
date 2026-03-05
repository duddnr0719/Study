package com.example.f1manager;

import lombok.RequiredArgsConstructor;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor

public class InitData implements CommandLineRunner {
    private final DriverRepository repository;

    @Override
    public void run(String... args) {
        Driver d1 = new Driver();
        d1.setName("Max Verstappen");
        d1.setTeam("Red Bull");
        d1.setPoints(33);
        repository.save(d1);

        Driver d2 = new Driver();
        d2.setName("Lewis Hamilton");
        d2.setTeam("Ferrari");
        d2.setPoints(22);
        repository.save(d2);

        System.out.println("기초 데이터 세팅 완료");
    }
}
