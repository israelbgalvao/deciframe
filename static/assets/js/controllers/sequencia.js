angular.module('deciframeApp').controller('SequenciaController', function($http, $window, ngProgressFactory, $anchorScroll, $location, GENEROS) {
  var vm = this;
  var apiUrl = "";
  var corPadrao = "#2E1C74";

  vm.sequenciasFamosas = [];
  vm.novaSequencia = { nome: "", acordes: "" };
  vm.mensagem = "";
  vm.minhaSequencia = {};
  vm.isSearching = false;
  vm.showSearchResultsCount = false;
  vm.esfigeSpeech =  "";
  vm.musics = [];
  vm.generos = GENEROS;
  vm.meuGenero = "";
  vm.progressbar = ngProgressFactory.createInstance();

  var respostaJson = function(dados) {
    if (typeof dados === "string") {
      try {
        return angular.fromJson(dados);
      } catch (e) {
        return {};
      }
    }
    return dados || {};
  };

  var converterSequencia = function(sequencia) {
    var acordes = [];
    if (sequencia && sequencia.acordes) {
      for (var i = 0; i < sequencia.acordes.length; i++) {
        acordes.push({ acorde: sequencia.acordes[i], cor: corPadrao });
      }
    }
    return {
      nome: sequencia ? sequencia.nome : "",
      acordes: acordes
    };
  };

  var carregarSequencias = function() {
    return $http.get(apiUrl.concat("sequencias")).then(function(response) {
      var dados = respostaJson(response.data);
      vm.sequenciasFamosas = [];
      if (angular.isArray(dados)) {
        for (var i = 0; i < dados.length; i++) {
          vm.sequenciasFamosas.push(converterSequencia(dados[i]));
        }
      }
      return vm.sequenciasFamosas;
    });
  };

  vm.temAcorde = function(acorde) {
    if (vm.minhaSequencia.acordes) {
      return (vm.minhaSequencia.acordes.indexOf(acorde) > -1);
    } else {
      return false;
    }
  }

  var createChordsString = function(chords) {
    var str = "";
    for (var i = 0; i < chords.length; i++) {
      str = str.concat(chords[i].acorde, ',');
    }
    return str.substring(0, str.length-1);
  }

  vm.pesquisarPorSequencia = function(sequencia) {
    if (sequencia) {
      vm.minhaSequencia = sequencia;
    }
    vm.progressbar.start();
    vm.esfigeSpeech = "Procurando músicas com base na sequencia...";
    vm.isSearching = true;
    vm.musics = [];

    var searchString = "similares?sequencia=".concat(createChordsString(vm.minhaSequencia.acordes));
    if (vm.meuGenero !== "" && vm.meuGenero !== null) {
      searchString += "&generos="+vm.meuGenero;
    }
    $http.get(apiUrl.concat(searchString))
      .success(function(data) {
        vm.progressbar.complete();
        vm.esfigeSpeech = "Encontrei essas músicas";
        vm.isSearching = false;
        vm.showSearchResultsCount = true;
        vm.musics = data;
      })
      .error(function(data) {
        vm.esfigeSpeech = "Ops! Algo errado.";
        vm.isSearching = false;
        vm.showSearchResultsCount = false;
      });
  }

  vm.cadastrarSequencia = function() {
    vm.mensagem = "";
    return $http.post(apiUrl.concat("sequencias"), {
      nome: vm.novaSequencia.nome,
      acordes: vm.novaSequencia.acordes
    }).then(function(response) {
      var dados = respostaJson(response.data);
      vm.mensagem = response.status === 201
        ? "Sequência cadastrada!"
        : "Essa sequência já existia.";
      var sequencia = converterSequencia(dados.sequencia);
      return carregarSequencias().then(function() {
        if (sequencia.acordes.length) {
          vm.pesquisarPorSequencia(sequencia);
        }
      });
    }, function(response) {
      var dados = respostaJson(response.data);
      vm.mensagem = dados.erro || "Ops! Algo errado.";
    });
  };

  vm.limparPesquisa = function() {
    vm.minhaSequencia = {};
    vm.musics = [];
  }

  vm.goToLirics = function(music) {
    $window.open(music.url);
  };

  vm.goToResults = function() {
    vm.showSearchResultsCount = false;
    $("body").animate({scrollTop: $("#results").offset().top}, "slow");
  };

  carregarSequencias();
});
