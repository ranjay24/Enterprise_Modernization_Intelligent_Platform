package com.training;

import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
public class TrainingController {

    private final TrainingService service;

    public TrainingController(TrainingService service) {
        this.service = service;
    }

    @GetMapping("/api/trainings")
    public List<Training> listTrainings() {
        return service.findAll();
    }

    @DeleteMapping("/api/trainings/{id}")
    public void deleteTraining(@PathVariable Long id) {
        service.delete(id);
    }
}
