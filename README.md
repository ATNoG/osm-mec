*Tested with OSM Release 17*

![osm-logo](osm-mec-logo.png)

<div align="center">
  
  >A Multi-access Edge Computing implementation on OSM
  
  
  <br>
  
  **<kbd> <br> [Promo Video](https://www.youtube.com/watch?v=NGTCEbkJ_D4) <br> </kbd>**
  **<kbd> <br> [Get Started / Wiki](https://atnog.github.io/osm-mec-wiki/) <br> </kbd>**
  **<kbd> <br> [Demo](https://www.youtube.com/watch?v=o9OZxs9vXEQ) <br> </kbd>**
  **<kbd> <br> [API Docs](https://app.swaggerhub.com/apis-docs/HenriqueCruz/oss-nb_api/1.0.0#/) <br> </kbd>**
  **<kbd> <br> [MEC APP descriptor Parameters](https://atnog.github.io/osm-mec/mec-app-descriptor-parameters) <br> </kbd>**
  **<kbd> <br> [Website](https://atnog.github.io/osm-mec/) <br> </kbd>**
  **<kbd> <br> [Poster](students-at-deti-poster.pdf) <br> </kbd>**
  **<kbd> <br> [HELM index](https://atnog.github.io/osm-mec/index.yaml) <br> </kbd>**

</div>

## Features

- This MEC platform implements some of the ETSI specifications for MEC. It works with OSM, using it to orchestrate and manage MEC applications as CNFs, "translating" MEC application descriptors to the corresponding NSs and CNFs.
- The developed MEAO allows MEC application migration, both in single-domain and federated scenarios. To achieve this, it collects metrics from the orchestrated Kubernetes clusters (where MEC Applications are installed) and triggers migration according to the necessities defined in the MEC application SLA. To achieve migration in federated scenarios, it uses the [MEC Federator developed in the ATNoG group](https://github.com/ATNoG/mec-federator/tree/main).

## Publications
- P. Pereira, P. Escaleira, D. Gomes and R. Aguiar, "Automatic Service Migration in a MEC-NFV Environment," 2024 IEEE Conference on Network Function Virtualization and Software Defined Networks (NFV-SDN), Natal, Brazil, 2024, pp. 1-7, doi: [10.1109/NFV-SDN61811.2024.10807471](https://www.doi.org/10.1109/NFV-SDN61811.2024.10807471).

## Contributors

- [Afonso Castanheta](https://github.com/castanheta)
- [Francisco Cardita](https://github.com/FranciscoCardita)
- [Henrique Cruz](https://github.com/hmecruz)
- [Luís Oliveira](https://github.com/luisOliveira-22)
- [Pedro Ferreira](https://github.com/PedroDSFerreira)
- [Samuel Teixeira](https://github.com/SamuTheCoder)
