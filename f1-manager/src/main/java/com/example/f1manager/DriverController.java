package com.example.f1manager;

import lombok.Getter;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController
@RequiredArgsConstructor
@RequestMapping("/drivers")

public class DriverController {
    private final DriverRepository repository;

    @GetMapping
    public List<Driver> getAll() {
        return repository.findAll();
    }
    @PostMapping
    public Driver add(@RequestBody Driver driver) {
        return repository.save(driver);
    }
}
